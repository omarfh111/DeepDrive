# TestDrive/ml_model.py
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import accuracy_score
import joblib
import os
from django.conf import settings


class NoShowPredictor:
    def __init__(self):
        self.model = None
        self.label_encoders = {}
        self.scaler = StandardScaler()

        self.features = [
            'lead_time', 'day_of_week', 'hour_of_day', 'duration',
            'car_marque_encoded', 'car_modele_encoded', 'location_encoded',
            'no_show_history', 'reservation_count'
        ]

        self.model_path = os.path.join(settings.BASE_DIR, 'testdrive_model.joblib')

        print("🔍 Initialisation du prédicteur IA...")
        self.load_model()

    def load_model(self):
        """Charge le modèle entraîné. Ne réentraîne jamais automatiquement."""
        if not os.path.exists(self.model_path):
            print("❌ Aucun modèle entraîné trouvé. Lance 'train_model.py' avant d'utiliser le prédicteur.")
            self.model = None
            return

        try:
            data = joblib.load(self.model_path)
            self.model = data['model']
            self.label_encoders = data['label_encoders']
            self.scaler = data['scaler']
            self.features = data['features']
            print("✅ Modèle IA chargé avec succès")
        except Exception as e:
            print(f"❌ Erreur lors du chargement du modèle: {e}")
            self.model = None

    def prepare_testdrive_features(self, testdrive):
        features = {}

        if testdrive.reservation_date and testdrive.created_at:
            lead_time = (testdrive.reservation_date - testdrive.created_at.date()).days
            features['lead_time'] = max(0, lead_time)
        else:
            features['lead_time'] = 7

        features['day_of_week'] = (
            testdrive.reservation_date.weekday() if testdrive.reservation_date else 2
        )

        features['hour_of_day'] = (
            testdrive.reservation_time.hour if testdrive.reservation_time else 14
        )

       
        features['car_marque'] = testdrive.car.marque if testdrive.car else "Unknown"
        features['car_modele'] = testdrive.car.modele if testdrive.car else "Unknown"
        features['location'] = testdrive.test_location or "Tunis"

        features['duration'] = testdrive.duration or 30
        features['no_show_history'] = testdrive.no_show_history or 0
        features['reservation_count'] = testdrive.reservation_count or 1

        return features

    def predict_binary(self, testdrive):
        if self.model is None:
            print("⚠️ Modèle IA non chargé.")
            return {'prediction': 0, 'probability': 0.0, 'confidence': 'Faible'}

        try:
            features_dict = self.prepare_testdrive_features(testdrive)
            df = pd.DataFrame([features_dict])

            for col in ['car_marque', 'car_modele', 'location']:
                encoded_col = f"{col}_encoded"

                if col not in self.label_encoders:
                    print(f"⚠️ Aucun encodage enregistré pour {col}.")
                    df[encoded_col] = 0
                    continue

                encoder = self.label_encoders[col]

                val = features_dict[col].strip().lower()

                classes = [c.lower() for c in encoder.classes_]

                if val in classes:
                    df[encoded_col] = encoder.transform([encoder.classes_[classes.index(val)]])
                else:
                    if "other" in classes:
                        df[encoded_col] = encoder.transform(["Other"])
                    else:
                        df[encoded_col] = 0

            for feature in self.features:
                if feature not in df.columns:
                    df[feature] = 0

            X = self.scaler.transform(df[self.features])

            prediction = int(self.model.predict(X)[0])
            probability = float(self.model.predict_proba(X)[0][1])

            result = {
                'prediction': prediction,
                'probability': probability,
                'confidence': (
                    "Élevée" if probability > 0.7 or probability < 0.3 else "Moyenne"
                )
            }

            print(f"🎯 Résultat prédiction IA: {result}")
            return result

        except Exception as e:
            print(f"❌ Erreur IA: {e}")
            return {'prediction': 0, 'probability': 0.0, 'confidence': 'Faible'}

predictor = NoShowPredictor()
