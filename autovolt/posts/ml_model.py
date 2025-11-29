import torch
import io
import base64
from pathlib import Path
from PIL import Image
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
import torchvision.transforms as T
from openai import OpenAI
from django.conf import settings

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Device configuration
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ----- Load detection model once -----
num_classes = 2  # background + odometer
model = fasterrcnn_resnet50_fpn(weights="DEFAULT")
in_features = model.roi_heads.box_predictor.cls_score.in_features
model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)

MODEL_PATH = Path(settings.BASE_DIR) / "models" / "best_f1_model.pth"
model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
model.to(device)
model.eval()

# Transforms
mean = [0.2897, 0.2526, 0.2432]
std  = [0.2187, 0.1923, 0.1776]

det_tfms = T.Compose([
    T.ToTensor(),
    T.Normalize(mean=mean, std=std),
])


def call_openai_vision_for_km(crop_pil: Image.Image) -> str:
    """
    Send cropped odometer image to OpenAI vision model and
    return only the digit string (e.g. '178049').
    """
    buf = io.BytesIO()
    crop_pil.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    prompt = (
        "You see a car odometer or trip/total km display. "
        "Read the value of the kilometers. "
        "Return ONLY the digits in order, no spaces, no commas, "
        "no units, no text, no explanation."
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
        max_tokens=20,
        temperature=0.0,
    )

    text = resp.choices[0].message.content.strip()
    digits_only = "".join(ch for ch in text if ch.isdigit())
    print(f"[OCR] raw='{text}' -> digits='{digits_only}'")
    return digits_only


def extract_kilometrage_from_image(image_file, score_thr: float = 0.4):
    """
    Extract kilometrage from uploaded dashboard image.

    Args:
        image_file: Django UploadedFile or file path (str / Path)
        score_thr: detection confidence threshold

    Returns:
        dict with box, det_score, kilometrage

    Raises:
        ValueError si aucun odomètre détecté ou si aucun chiffre n’est lu.
    """
    try:
        model.eval()

        # ----- Read uploaded file safely -----
        if isinstance(image_file, (str, Path)):
            pil_img = Image.open(image_file).convert("RGB")
        else:
            # Django InMemoryUploadedFile / TemporaryUploadedFile
            data = image_file.read()
            image_file.seek(0)          # reset pointer so Django can re-use it
            pil_img = Image.open(io.BytesIO(data)).convert("RGB")

        img_tensor = det_tfms(pil_img).to(device)

        with torch.no_grad():
            out = model([img_tensor])[0]

        boxes = out["boxes"].cpu()
        scores = out["scores"].cpu()
        labels = out["labels"].cpu()

        print(f"[DET] labels={labels.tolist()[:10]} scores={scores.tolist()[:10]}")

        # odometer = class 1
        keep = (labels == 1) & (scores >= score_thr)
        if keep.sum().item() == 0:
            # ---> ICI : pas de bounding box
            raise ValueError(
                "Aucun compteur kilométrique n'a été détecté sur l'image. "
                "Veuillez téléverser une photo plus centrée et nette du compteur."
            )

        boxes = boxes[keep]
        scores = scores[keep]

        best_idx = scores.argmax().item()
        x1, y1, x2, y2 = map(int, boxes[best_idx].tolist())
        best_score = scores[best_idx].item()

        print(f"[DET] best box={x1,y1,x2,y2} score={best_score:.3f}")

        crop = pil_img.crop((x1, y1, x2, y2))

        # ----- OCR -----
        km_digits = call_openai_vision_for_km(crop)

        if not km_digits:
            # ---> ICI : bbox trouvée mais pas de chiffres lisibles
            raise ValueError(
                "Le compteur a été détecté mais le kilométrage n'a pas pu être lu. "
                "Veuillez vérifier que les chiffres sont bien visibles."
            )

        return {
            "box": (x1, y1, x2, y2),
            "det_score": best_score,
            "kilometrage": float(km_digits),
        }

    except Exception as e:
        # On laisse remonter l'erreur pour qu'elle soit gérée dans la vue
        print(f"[ERROR] extract_kilometrage_from_image: {e!r}")
        raise

def verify_car_image(image_file, required_confidence: float = 0.6) -> bool:
    """
    Use OpenAI Vision (gpt-4o-mini) to verify that the uploaded image
    really contains a car (photo, interior, dashboard, etc.).

    Returns:
        True  -> looks like a real car image
        False -> not a real car / logo / toy / drawing / etc.
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
        return True
