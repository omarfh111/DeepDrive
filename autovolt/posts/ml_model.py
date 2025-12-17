import torch
import os
import io
import base64
from pathlib import Path
from PIL import ImageEnhance, ImageFilter,Image
import torch.nn as nn
import torch.nn.functional as F
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
import torchvision.transforms as T
from torchvision import transforms
from torchvision.transforms import InterpolationMode
from openai import OpenAI
from django.conf import settings
import timm
import json
import joblib
import pandas as pd
client = OpenAI(api_key=settings.OPENAI_API_KEY)


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


num_classes = 2  
model = fasterrcnn_resnet50_fpn(weights="DEFAULT")
in_features = model.roi_heads.box_predictor.cls_score.in_features
model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)

MODEL_PATH = Path(settings.BASE_DIR) / "models" / "best_f1_model.pth"

model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
model.to(device)
model.eval()


mean = [0.2897, 0.2526, 0.2432]
std  = [0.2187, 0.1923, 0.1776]

det_tfms = T.Compose([
    T.ToTensor(),
    T.Normalize(mean=mean, std=std),
])


def call_openai_vision_for_km(crop_pil: Image.Image) -> str:
    """
    Send cropped odometer image to OpenAI vision model with enhanced prompt.
    Returns only the digit string (e.g. '178049').
    """
    # Enhance image before sending to API
    from PIL import ImageEnhance, ImageFilter
    
    # Upscale if too small
    w, h = crop_pil.size
    if w < 300 or h < 300:
        scale = max(300 / w, 300 / h)
        new_w, new_h = int(w * scale), int(h * scale)
        crop_pil = crop_pil.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Enhance contrast and sharpness
    enhancer = ImageEnhance.Contrast(crop_pil)
    crop_pil = enhancer.enhance(2.0)  # Stronger contrast
    enhancer = ImageEnhance.Sharpness(crop_pil)
    crop_pil = enhancer.enhance(2.0)  # Stronger sharpness
    
    # Apply unsharp mask for better digit clarity
    crop_pil = crop_pil.filter(ImageFilter.UnsharpMask(radius=2, percent=150))
    
    buf = io.BytesIO()
    crop_pil.save(buf, format="PNG")
    img_bytes = buf.getvalue()
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    # Ultra-specific prompt for small digital displays
    prompt = """You are analyzing a CROPPED image from a car dashboard odometer/kilometrage display.

CRITICAL INSTRUCTIONS:
1. This image may show VERY SMALL digits - look extremely carefully at ANY numbers visible
2. The digits might be: LCD/LED display, seven-segment display, or digital font
3. Numbers may be as small as 1-2 digits (like "7" or "17") or as large as 6-7 digits
4. Look for these indicators near numbers: "km", "KM", "ODO", "TRIP", "TOTAL", distance icon (🛣️)

WHAT TO IGNORE:
- Speed readings (usually larger, near "MPH" or "KPH" labels)
- RPM gauge numbers (near "x1000" or "RPM")
- Fuel gauge numbers
- Temperature readings
- Clock/time displays

WHAT TO FIND:
- The ODOMETER or TRIP METER reading specifically
- Usually the smallest text/numbers in the display
- Often in a separate small digital window or panel
- May have leading zeros (like "000017" for 17 km)

EXAMPLES:
Input: Small LCD showing "4145 km" → Output: 4145
Input: Seven-segment display "178049" → Output: 178049  
Input: Tiny display showing "ODO 0017" → Output: 17
Input: Mixed display with "80" (speed) and small "17" near km label → Output: 17

INSTRUCTIONS:
- Look at EVERY number in the image, especially the smallest ones
- If you see multiple numbers, choose the one associated with distance/odometer labels
- Remove any leading zeros UNLESS the number is all zeros
- Return ONLY the digits, no spaces, commas, or text
- If absolutely cannot read any kilometrage number, return: UNREADABLE

Your answer (digits only or UNREADABLE):"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",  # Use gpt-4o for better vision understanding
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_b64}",
                            "detail": "high"  # Request high detail analysis
                        },
                    },
                ],
            }
        ],
        max_tokens=50,  # Increased for reasoning
        temperature=0.0,
    )

    text = resp.choices[0].message.content.strip()
    
    # Handle UNREADABLE response
    if "UNREADABLE" in text.upper():
        print(f"[OCR] Model couldn't read the display: {text}")
        return ""
    
    # Extract digits
    digits_only = "".join(ch for ch in text if ch.isdigit())
    print(f"[OCR] raw='{text}' -> digits='{digits_only}'")
    
    return digits_only


def extract_kilometrage_from_image(
    image_file, 
    score_thr: float = 0.4,
    retry_with_lower_threshold: bool = True
):
    """
    Extract kilometrage from uploaded dashboard image with enhanced robustness.

    Args:
        image_file: Django UploadedFile or file path (str / Path)
        score_thr: initial detection confidence threshold
        retry_with_lower_threshold: if True, retry with lower threshold on failure

    Returns:
        dict with box, det_score, kilometrage, and confidence_level

    Raises:
        ValueError if no odometer detected or no digits readable
    """
    try:
        model.eval()

        
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
                    retry_with_lower_threshold=False
                )
            
            raise ValueError(
                "Aucun compteur kilométrique n'a été détecté sur l'image. "
                "Conseils : Assurez-vous que le tableau de bord est bien visible, "
                "centré, et que l'éclairage est suffisant. Évitez les reflets."
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
            
      
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(crop)
            crop = enhancer.enhance(1.5)
            enhancer = ImageEnhance.Sharpness(crop)
            crop = enhancer.enhance(1.3)
            
            km_digits = call_openai_vision_for_km(crop)
            
            if km_digits and len(km_digits) >= 1: 
                km_value = float(km_digits)
                
                if 1 <= km_value <= 9999999:
                    confidence = "high" if current_score >= 0.7 else "medium" if current_score >= 0.5 else "low"
                    
                    return {
                        "box": (x1, y1, x2, y2),
                        "det_score": current_score,
                        "kilometrage": km_value,
                        "confidence_level": confidence,
                        "attempts": sorted_indices.tolist().index(idx) + 1
                    }
                else:
                    print(f"[OCR] Rejected unrealistic value: {km_value}")
            
            print(f"[OCR] Box {idx} failed, trying next...")
        
        raise ValueError(
            "Le compteur a été détecté mais le kilométrage n'a pas pu être lu clairement. "
            "Veuillez vérifier que : "
            "1) Les chiffres du compteur sont nets et bien éclairés, "
            "2) Il n'y a pas de reflet sur l'écran, "
            "3) La photo est prise de face (pas en angle). "
            "Essayez de prendre une nouvelle photo plus proche du compteur."
        )

    except ValueError:
        raise
    except Exception as e:
        print(f"[ERROR] extract_kilometrage_from_image: {e!r}")
        raise ValueError(
            f"Erreur lors du traitement de l'image : {str(e)}. "
            "Veuillez réessayer avec une autre photo."
        )










def verify_car_image(image_file, required_confidence: float = 0.6) -> bool:
    """
    Validate that the image contains a passenger car (real-world photo OR studio/press shot).
    Accepts: road photos, studio/press photos, clean cutouts on white/transparent background.
    Rejects: logos, drawings, cartoons, toy cars, purely 3D concept art, screenshots/UI, text-only.
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
        img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        prompt = f"""
You are a strict validator for a car marketplace image upload.

Return ONLY a JSON object with keys:
- is_car: boolean
- confidence: number from 0.0 to 1.0
- reason: short string

ACCEPT (is_car=true) when the image clearly shows a passenger car or SUV:
- real photo (outdoor/road)
- interior/dashboard photo
- studio/press photo
- official catalog image
- cutout image on white/transparent background (PNG style)

REJECT (is_car=false) for:
- logos/brand badges alone
- drawings, cartoons, sketches, anime
- toy cars / miniatures
- screenshots of web pages or app UI
- text-only images
- images where no car body is clearly visible

Important:
- If a car is visible but could be a toy/drawing, lower confidence.
- If it is a clean studio/cutout but clearly a real car photo, confidence can still be high.
IMPORTANT RULE:
    If the image is a clean studio or catalog photo of a REAL production car
    (even on white or transparent background), set is_car=true and confidence >= 0.7.
Now analyze the image and output JSON only.
"""

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt.strip()},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}", "detail": "high"}},
                ],
            }],
            max_tokens=120,
            temperature=0.0,
        )

        raw = (resp.choices[0].message.content or "").strip()
        print(f"[CAR-VERIFY] raw='{raw}'")

        # Parse JSON robustly (avoid crashes if model adds stray text)
        import json, re
        m = re.search(r"\{.*\}", raw, flags=re.S)
        if not m:
            return False  # cannot parse => treat as not valid
        obj = json.loads(m.group(0))

        is_car = bool(obj.get("is_car", False))
        conf = float(obj.get("confidence", 0.0))
        reason = (obj.get("reason") or "").lower()
        if not is_car:
            return False

        if conf >= required_confidence:
            return True

        # Fallback for studio / press images
        STUDIO_KEYWORDS = [
            "studio", "press", "catalog", "cutout",
            "white background", "official", "promo"
        ]

        if any(k in reason for k in STUDIO_KEYWORDS) and conf >= 0.45:
            return True
        return False

    except Exception as e:
        print(f"[ERROR] verify_car_image: {e!r}")
        # keep your current non-blocking behavior
        return True










MODEL_DIR = Path(settings.BASE_DIR) / "models"
ENCODER_PATH = MODEL_DIR / "car_vit_encoder_make_model.pth"

IMG_SIZE = 224
MEAN = (0.5, 0.5, 0.5)
STD  = (0.5, 0.5, 0.5)
EMBED_DIM = 512

val_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE), interpolation=InterpolationMode.BICUBIC),
    transforms.CenterCrop(IMG_SIZE),
    transforms.ToTensor(),
    transforms.Normalize(mean=MEAN, std=STD),
])

class ViTEncoderOnly(nn.Module):
    """
    Rebuilds the training encoder:
      backbone: timm vit_base_patch16_224, num_classes=0
      embedding: Linear(in_features -> 512)
    Returns L2-normalized embeddings.
    """
    def __init__(self, embed_dim=512):
        super().__init__()
        self.backbone = timm.create_model(
            "vit_base_patch16_224",
            pretrained=False,   # IMPORTANT: we load trained weights from file
            num_classes=0
        )
        in_features = self.backbone.num_features
        self.embedding = nn.Linear(in_features, embed_dim)

    def forward(self, x):
        feats = self.backbone(x)
        emb = self.embedding(feats)
        emb = F.normalize(emb, p=2, dim=1)
        return emb

_embed_model = None
_embed_meta = None

def _load_encoder_state():
    """
    Loads your encoder_state dict:
      {
        "backbone": state_dict,
        "embedding": state_dict,
        "embed_dim": 512,
        "img_size": 224,
        "mean": [0.5,0.5,0.5],
        "std": [0.5,0.5,0.5],
      }
    """
    state = torch.load(str(ENCODER_PATH), map_location=device)

    if not isinstance(state, dict) or "backbone" not in state or "embedding" not in state:
        raise RuntimeError(
            "car_vit_encoder_make_model.pth is not in expected encoder_state format "
            "(missing 'backbone'/'embedding')."
        )
    return state

def get_car_embedder():
    """
    Singleton model loader (one load per process).
    """
    global _embed_model, _embed_meta
    if _embed_model is None:
        enc_state = _load_encoder_state()

        embed_dim = int(enc_state.get("embed_dim", EMBED_DIM))
        m = ViTEncoderOnly(embed_dim=embed_dim).to(device)

        m.backbone.load_state_dict(enc_state["backbone"], strict=True)
        m.embedding.load_state_dict(enc_state["embedding"], strict=True)

        m.eval()
        _embed_model = m
        _embed_meta = {
            "embed_dim": embed_dim,
            "img_size": int(enc_state.get("img_size", IMG_SIZE)),
            "mean": tuple(enc_state.get("mean", list(MEAN))),
            "std": tuple(enc_state.get("std", list(STD))),
        }

    return _embed_model, _embed_meta

@torch.no_grad()
def embed_car_image(image_file) -> list[float]:
    """
    image_file: Django UploadedFile / FieldFile OR a filesystem path (str/Path)
    Returns: list[float] of length 512 (L2-normalized).
    """
    model, meta = get_car_embedder()

    # Safety: if meta says different preprocessing, apply it
    img_size = meta["img_size"]
    mean = meta["mean"]
    std = meta["std"]

    tfm = transforms.Compose([
        transforms.Resize((img_size, img_size), interpolation=InterpolationMode.BICUBIC),
        transforms.CenterCrop(img_size),
        transforms.ToTensor(),
        transforms.Normalize(mean=mean, std=std),
    ])

    if isinstance(image_file, (str, Path)):
        pil_img = Image.open(image_file).convert("RGB")
    else:
        data = image_file.read()
        image_file.seek(0)
        pil_img = Image.open(io.BytesIO(data)).convert("RGB")

    x = tfm(pil_img).unsqueeze(0).to(device)
    emb = model(x).squeeze(0)           
    return emb.cpu().tolist()







_model = None
_features = None


def _load_artifacts():
    MODEL_PATH = os.path.join(settings.BASE_DIR, "models", "car_price_model.joblib")
    FEATURES_PATH = os.path.join(settings.BASE_DIR, "models", "features.json")
    global _model, _features
    if _model is None:
        _model = joblib.load(MODEL_PATH)
    if _features is None:
        with open(FEATURES_PATH, "r", encoding="utf-8") as f:
            _features = json.load(f)


def predict_car_price(*, annee: int, kilometrage: float, marque: str, modele: str) -> float:
    """
    Returns predicted fair price (float).
    """
    _load_artifacts()

    car = pd.DataFrame([{
        "annee": annee,
        "kilometrage": kilometrage,
        "marque": marque,
        "modele": modele,
    }])

    for col in _features:
        if col not in car.columns:
            car[col] = None
    car = car[_features]

    return float(_model.predict(car)[0])

def evaluate_offer(*, pred_price: float, seller_price: float):
    # threshold
    if pred_price < 45_000:
        threshold = 20
    elif pred_price < 90_000:
        threshold = 15
    elif pred_price < 150_000:
        threshold = 12
    else:
        threshold = 10

    # bias correction
    adj_pred = pred_price
    if adj_pred < 45_000:
        adj_pred *= 0.90
    if adj_pred > 150_000:
        adj_pred *= 1.05

    pct = ((seller_price - adj_pred) / adj_pred) * 100 if adj_pred else 0.0

    if pct > threshold:
        return float(adj_pred), "OVERPRICED"
    if pct < -threshold:
        return float(adj_pred), "GOOD_DEAL"
    return float(adj_pred), "NORMAL"



def predict_price_and_label(*, annee: int, kilometrage: float, marque: str, modele: str, seller_price: float):
    pred = predict_car_price(annee=annee, kilometrage=kilometrage, marque=marque, modele=modele)
    adj_pred, label = evaluate_offer(pred_price=pred, seller_price=seller_price)
    return adj_pred, label


    