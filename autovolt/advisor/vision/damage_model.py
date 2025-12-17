from pathlib import Path
import torch
from torchvision import models, transforms
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent
WEIGHTS_PATH = BASE_DIR / "weights" / "car_condition_resnet18.pth"

print(">> Chargement modèle ETAT depuis :", WEIGHTS_PATH)

if not WEIGHTS_PATH.exists():
    raise FileNotFoundError(f"Poids d'état introuvables : {WEIGHTS_PATH}")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

_checkpoint = torch.load(WEIGHTS_PATH, map_location=device)

_model = models.resnet18(weights=None)
class_to_idx = _checkpoint["class_to_idx"]
num_classes = len(class_to_idx)

in_features = _model.fc.in_features
_model.fc = torch.nn.Linear(in_features, num_classes)
_model.load_state_dict(_checkpoint["model_state_dict"])
_model = _model.to(device)
_model.eval()

_idx_to_class = {v: k for k, v in class_to_idx.items()}

_transform = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])

LABEL_MAP_FR = {
    "01-minor": "bon état",
    "02-moderate": "état moyen",
    "03-severe": "mauvais état",
}


def predict_damage(image: Image.Image):
    img = image.convert("RGB")
    x = _transform(img).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = _model(x)
        probs = torch.softmax(outputs, dim=1)
        conf, pred_idx = torch.max(probs, 1)

    label_raw = _idx_to_class[pred_idx.item()]
    confidence = float(conf.item())
    label_fr = LABEL_MAP_FR.get(label_raw, label_raw)

    return {
        "label_raw": label_raw,
        "label_fr": label_fr,
        "confidence": confidence,
    }
