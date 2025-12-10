# advisor/vision/brand_model.py

import json
from pathlib import Path

import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as T
from PIL import Image
from django.conf import settings

# --------- Device ----------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# --------- Chemins vers poids + classes ----------
WEIGHTS_PATH = (
    Path(settings.BASE_DIR)
    / "advisor"
    / "vision"
    / "weights"
    / "stanford_cars_resnet18.pth"
)

CLASSES_PATH = (
    Path(settings.BASE_DIR)
    / "advisor"
    / "vision"
    / "weights"
    / "stanford_cars_class_names.json"
)

# --------- Charger les labels Stanford Cars ----------
with open(CLASSES_PATH, "r", encoding="utf-8") as f:
    class_names = json.load(f)

num_classes = len(class_names)

# --------- Transforms (comme val_tfms dans le notebook) ----------
val_tfms = T.Compose([
    T.Resize((256, 256)),
    T.CenterCrop(224),
    T.ToTensor(),
    T.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])

# --------- Modèle ResNet18 ----------
model = models.resnet18(weights=None)
in_features = model.fc.in_features
model.fc = nn.Linear(in_features, num_classes)

state_dict = torch.load(WEIGHTS_PATH, map_location=device)
model.load_state_dict(state_dict)
model.to(device)
model.eval()


def _parse_label(full_label: str):
    """
    Découpe un label Stanford Cars du type :
    'Audi S5 Convertible 2012'
    en (brand='Audi', model_name='S5 Convertible', year=2012)
    """
    parts = full_label.split()
    brand = None
    model_name = None
    year = None

    if len(parts) >= 2:
        brand = parts[0]
        # essayer de lire l'année sur le dernier token
        try:
            year = int(parts[-1])
            if len(parts) > 2:
                model_name = " ".join(parts[1:-1])
        except ValueError:
            # pas d'année lisible, on met tout en modèle
            model_name = " ".join(parts[1:])

    return brand, model_name, year


def predict_brand(pil_img: Image.Image):
    """
    Entrée : image PIL (vue extérieure / globale).
    Sortie : dict avec :
      - brand         : marque (Audi, BMW, ...)
      - model_name    : modèle (S5 Convertible, M3 Coupe, ...)
      - year          : année (int ou None)
      - full_label    : label complet Stanford
      - confidence    : probabilité max
      - status        : 'confiant' | 'moyen' | 'faible'
    """
    img = pil_img.convert("RGB")
    img_tensor = val_tfms(img).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(img_tensor)
        probs = torch.softmax(outputs, dim=1)[0]
        conf, pred_idx = torch.max(probs, dim=0)

    conf = float(conf)
    pred_idx = int(pred_idx)
    full_label = class_names[pred_idx]

    brand, model_name, year = _parse_label(full_label)

    # statut de confiance (pour la badge dans le front)
    if conf >= 0.7:
        status = "confiant"
    elif conf >= 0.4:
        status = "moyen"
    else:
        status = "faible"

    return {
        "brand": brand or full_label,
        "model_name": model_name,
        "year": year,
        "full_label": full_label,
        "confidence": conf,
        "status": status,
    }
