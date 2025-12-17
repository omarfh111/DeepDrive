import requests
from PIL import Image
from io import BytesIO

ROBOFLOW_API_KEY = "Q2zZzhyNB8MtmjfNTNrR"  # ⚠️ mets ta clé
ROBOFLOW_MODEL = "car-dashboard-icons/3"
ROBOFLOW_URL = f"https://detect.roboflow.com/{ROBOFLOW_MODEL}"
 

def predict_dashboard_icon_api(pil_image):
    """
    Envoie l’image au modèle Roboflow et renvoie les prédictions.
    """

    # Convertir PIL → bytes jpg
    img_buffer = BytesIO()
    pil_image.save(img_buffer, format="JPEG")
    img_buffer.seek(0)

    response = requests.post(
        ROBOFLOW_URL,
        params={"api_key": ROBOFLOW_API_KEY},
        files={"file": img_buffer},
    )

    data = response.json()
    return data
