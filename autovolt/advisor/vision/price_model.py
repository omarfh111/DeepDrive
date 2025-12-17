# advisor/vision/price_model.py
import os
import joblib
import pandas as pd

_MODEL = None

def _load_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    base_dir = os.path.dirname(__file__)
    model_path = os.path.join(base_dir, "weights", "car_price_model.joblib")

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Price model introuvable: {model_path}")

    _MODEL = joblib.load(model_path)
    return _MODEL


def predict_car_price(annee: int, kilometrage: float, marque: str, modele: str) -> float:
    """
    Retourne un prix (float).
    Supporte :
    - Pipeline sklearn entraîné avec DataFrame (colonnes)
    - Modèle entraîné avec liste simple
    """
    model = _load_model()

    annee = int(annee)
    kilometrage = float(kilometrage)
    marque = str(marque).strip()
    modele = str(modele).strip()

    # ✅ si le pipeline a été entraîné avec des colonnes, on envoie un DataFrame
    if hasattr(model, "feature_names_in_"):
        cols = list(model.feature_names_in_)
        row = {
            cols[0]: annee,
            cols[1]: kilometrage,
            cols[2]: marque,
            cols[3]: modele,
        }
        X = pd.DataFrame([row], columns=cols)
        y = model.predict(X)
        return float(y[0])

    # fallback : liste
    X = [[annee, kilometrage, marque, modele]]
    y = model.predict(X)
    return float(y[0])
