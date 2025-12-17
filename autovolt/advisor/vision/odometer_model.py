import io
import base64
from pathlib import Path

import torch
import torchvision.transforms as T
from PIL import ImageEnhance, ImageFilter, Image
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

from openai import OpenAI
from django.conf import settings

# =======================
# 🔹 OpenAI client
# =======================
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# =======================
# 🔹 Device
# =======================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# =======================
# 🔹 Load detection model (odometer)
# =======================

num_classes = 2  # background + odometer

model = fasterrcnn_resnet50_fpn(weights="DEFAULT")
in_features = model.roi_heads.box_predictor.cls_score.in_features
model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)

# 💡 Place ton poids dans advisor/vision/weights/odometer_best_f1.pth
MODEL_PATH = (
    Path(settings.BASE_DIR)
    / "advisor"
    / "vision"
    / "weights"
    / "best_f1_model.pth"
)

model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
model.to(device)
model.eval()

# =======================
# 🔹 Transforms
# =======================
mean = [0.2897, 0.2526, 0.2432]
std  = [0.2187, 0.1923, 0.1776]

det_tfms = T.Compose([
    T.ToTensor(),
    T.Normalize(mean=mean, std=std),
])


# =======================
# 🔹 OpenAI Vision – OCR KM
# =======================
def _call_openai_vision_for_km(crop_pil: Image.Image) -> str:
    """
    Envoie l'image du compteur à OpenAI et renvoie une string de digits (ex: '178049').
    Renvoie "" si illisible.
    """
    # upscale si trop petit
    w, h = crop_pil.size
    if w < 300 or h < 300:
        scale = max(300 / w, 300 / h)
        new_w, new_h = int(w * scale), int(h * scale)
        crop_pil = crop_pil.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Constraste + netteté
    enhancer = ImageEnhance.Contrast(crop_pil)
    crop_pil = enhancer.enhance(2.0)
    enhancer = ImageEnhance.Sharpness(crop_pil)
    crop_pil = enhancer.enhance(2.0)
    crop_pil = crop_pil.filter(ImageFilter.UnsharpMask(radius=2, percent=150))

    buf = io.BytesIO()
    crop_pil.save(buf, format="PNG")
    img_bytes = buf.getvalue()
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    prompt = """You are analyzing a CROPPED image from a car dashboard odometer/kilometrage display.

CRITICAL INSTRUCTIONS:
1. This image may show VERY SMALL digits - look extremely carefully at ANY numbers visible
2. The digits might be: LCD/LED display, seven-segment display, or digital font
3. Numbers may be as small as 1-2 digits or as large as 6-7 digits
4. Look for: 'km', 'KM', 'ODO', 'TRIP', 'TOTAL', or distance icons.

IGNORE:
- Speed (MPH/KPH), RPM, fuel, temperature, clock/time.

RETURN:
- Only the odometer/trip reading as digits.
- If unreadable, return UNREADABLE.

Your answer (digits only or UNREADABLE):"""

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_b64}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
        max_tokens=50,
        temperature=0.0,
    )

    text = (resp.choices[0].message.content or "").strip()
    if "UNREADABLE" in text.upper():
        print(f"[OCR] UNREADABLE: {text}")
        return ""

    digits_only = "".join(ch for ch in text if ch.isdigit())
    print(f"[OCR] raw='{text}' -> digits='{digits_only}'")
    return digits_only


# =======================
# 🔹 Public: lire le kilométrage
# =======================
def extract_kilometrage_from_image(
    image_file,
    score_thr: float = 0.4,
    retry_with_lower_threshold: bool = True,
):
    """
    Principal point d'entrée pour ton advisor:
    - Détecte le compteur avec FasterRCNN
    - Crop
    - Envoie à OpenAI Vision
    - Retourne dict:
      {
        "box": (x1, y1, x2, y2),
        "det_score": float,
        "kilometrage": float,
        "confidence_level": 'high'|'medium'|'low',
        "attempts": int
      }
    """
    try:
        model.eval()

        # Lecture de l'image
        if isinstance(image_file, (str, Path)):
            pil_img = Image.open(image_file).convert("RGB")
        else:
            data = image_file.read()
            image_file.seek(0)
            pil_img = Image.open(io.BytesIO(data)).convert("RGB")

        img_tensor = det_tfms(pil_img).to(device)

        with torch.no_grad():
            out = model([img_tensor])[0]

        boxes = out["boxes"].cpu()
        scores = out["scores"].cpu()
        labels = out["labels"].cpu()

        print(f"[DET] Found {len(labels)} detections")
        print(f"[DET] Top 5 - labels={labels.tolist()[:5]} scores={scores.tolist()[:5]}")

        keep = (labels == 1) & (scores >= score_thr)

        if keep.sum().item() == 0:
            if retry_with_lower_threshold and score_thr > 0.2:
                print(f"[DET] No detections at {score_thr}, retrying at 0.25")
                return extract_kilometrage_from_image(
                    image_file,
                    score_thr=0.25,
                    retry_with_lower_threshold=False,
                )

            raise ValueError(
                "Aucun compteur kilométrique n'a été détecté sur l'image. "
                "Assurez-vous que le tableau de bord est bien visible, centré "
                "et correctement éclairé."
            )

        boxes_filtered = boxes[keep]
        scores_filtered = scores[keep]

        sorted_indices = scores_filtered.argsort(descending=True)

        for idx in sorted_indices[:3]:
            x1, y1, x2, y2 = map(int, boxes_filtered[idx].tolist())
            current_score = scores_filtered[idx].item()

            print(f"[DET] Trying box {idx}: ({x1},{y1},{x2},{y2}) score={current_score:.3f}")

            w, h = pil_img.size
            pad_x = int((x2 - x1) * 0.05)
            pad_y = int((y2 - y1) * 0.05)

            x1 = max(0, x1 - pad_x)
            y1 = max(0, y1 - pad_y)
            x2 = min(w, x2 + pad_x)
            y2 = min(h, y2 + pad_y)

            crop = pil_img.crop((x1, y1, x2, y2))

            enhancer = ImageEnhance.Contrast(crop)
            crop = enhancer.enhance(1.5)
            enhancer = ImageEnhance.Sharpness(crop)
            crop = enhancer.enhance(1.3)

            km_digits = _call_openai_vision_for_km(crop)

            if km_digits and len(km_digits) >= 1:
                km_value = float(km_digits)

                if 1 <= km_value <= 9_999_999:
                    if current_score >= 0.7:
                        confidence = "high"
                    elif current_score >= 0.5:
                        confidence = "medium"
                    else:
                        confidence = "low"

                    return {
                        "box": (x1, y1, x2, y2),
                        "det_score": current_score,
                        "kilometrage": km_value,
                        "confidence_level": confidence,
                        "attempts": sorted_indices.tolist().index(idx) + 1,
                    }
                else:
                    print(f"[OCR] Rejected unrealistic value: {km_value}")

            print(f"[OCR] Box {idx} failed, trying next...")

        raise ValueError(
            "Le compteur a été détecté mais le kilométrage n'a pas pu être lu clairement. "
            "Essayez une photo plus nette, bien éclairée, prise de face."
        )

    except ValueError:
        raise
    except Exception as e:
        print(f"[ERROR] extract_kilometrage_from_image: {e!r}")
        raise ValueError(
            f"Erreur lors du traitement de l'image : {str(e)}. "
            "Veuillez réessayer avec une autre photo."
        )


# =======================
# 🔹 Vérifier si l'image est bien une voiture
# =======================
def verify_car_image(image_file, required_confidence: float = 0.6) -> bool:
    """
    Utilise OpenAI Vision (gpt-4o-mini) pour vérifier que l'image
    contient bien une voiture réelle (extérieur, intérieur, dashboard).
    Retourne True/False.
    """
    try:
        if isinstance(image_file, (str, Path)):
            pil_img = Image.open(image_file).convert("RGB")
        else:
            data = image_file.read()
            image_file.seek(0)
            pil_img = Image.open(io.BytesIO(data)).convert("RGB")

        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        img_bytes = buf.getvalue()
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")

        prompt = (
            "You are a strict image validator for an online used car marketplace.\n"
            "You receive one image. Answer ONLY with a single word: YES or NO.\n\n"
            "Answer YES if and only if the image clearly contains a *real* car "
            "(exterior, interior, or dashboard of a real passenger vehicle) "
            "in a photographic style.\n"
            "Answer NO for: logos, drawings, cartoons, toy cars, 3D renders, "
            "screenshots, advertisements, catalog mockups, or any image where "
            "no real car is visible."
        )

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                        },
                    ],
                }
            ],
            max_tokens=5,
            temperature=0.0,
        )

        text = (resp.choices[0].message.content or "").strip().upper()
        print(f"[CAR-VERIFY] raw='{text}'")
        return text.startswith("YES")

    except Exception as e:
        print(f"[ERROR] verify_car_image: {e!r}")
        # par défaut on laisse passer pour ne pas bloquer tout
        return True
