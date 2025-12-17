# advisor/vision/icons_api.py

from io import BytesIO

from django.conf import settings
from inference_sdk import InferenceHTTPClient
from PIL import Image

# 🔑 Lis la clé depuis settings (à mettre dans .env ou settings.py)
ROBOFLOW_API_KEY = getattr(settings, "ROBOFLOW_API_KEY", None)

CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="Q2zZzhyNB8MtmjfNTNrR",
)

MODEL_ID = "car-dashboard-icons/3"   # ton model_id Roboflow


def detect_dashboard_icons(django_file):
    """
    django_file : InMemoryUploadedFile (request.FILES['image'])
    Retourne une liste de voyants sous forme:
    [
      {"label": "...", "confidence": 0.87, "x": ..., "y": ..., "width": ..., "height": ...},
      ...
    ]
    """

    # 1) Lire le contenu du fichier une seule fois
    raw = django_file.read()
    django_file.seek(0)

    # 2) Charger en PIL (type accepté par inference_sdk)
    img = Image.open(BytesIO(raw)).convert("RGB")

    # 3) Appel Roboflow (⚠️ PAS de param 'confidence' ici)
    result = CLIENT.infer(img, model_id=MODEL_ID)

    preds = result.get("predictions", [])
    lights = []

    for p in preds:
        conf = float(p.get("confidence", 0.0))
        label = p.get("class", "Unknown")

        # petit seuil pour filtrer les très mauvaises prédictions
        if conf < 0.5:
            continue

        lights.append({
            "label": label,
            "confidence": conf,
            "x": p.get("x"),
            "y": p.get("y"),
            "width": p.get("width"),
            "height": p.get("height"),
        })

    return lights
