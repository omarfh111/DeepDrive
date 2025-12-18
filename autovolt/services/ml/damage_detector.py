"""
Détecteur de dommages automobiles avec YOLOv8 Segmentation
Mode CPU uniquement - Compatible Django - PyTorch 2.9.1
"""
import os
import warnings

# Désactiver TOUS les warnings
warnings.filterwarnings('ignore')
os.environ['YOLO_VERBOSE'] = 'False'

import torch

# FIX PYTORCH 2.6+ : Patcher Ultralytics AVANT l'import
import ultralytics.nn.tasks

# Sauvegarder la fonction originale
_original_torch_safe_load = ultralytics.nn.tasks.torch_safe_load

def _patched_torch_safe_load(weight):
    """Version patchée qui force weights_only=False"""
    try:
        # Essayer avec weights_only=False
        return torch.load(weight, map_location='cpu', weights_only=False), weight
    except Exception as e:
        # Si ça échoue, utiliser la méthode originale
        return _original_torch_safe_load(weight)

# Appliquer le patch
ultralytics.nn.tasks.torch_safe_load = _patched_torch_safe_load

# Maintenant importer YOLO
from ultralytics import YOLO
from PIL import Image
import cv2
import numpy as np
from pathlib import Path


class DamageDetector:
    """Détecteur de dommages sur voitures avec YOLOv8-Seg"""
    
    def __init__(self, model_path=None):
        """
        Initialise le détecteur
        
        Args:
            model_path: Chemin vers best.pt (optionnel)
        """
        # Forcer CPU
        torch.set_num_threads(1)
        
        # Chemin par défaut
        if model_path is None:
            model_path = os.path.join(
                os.path.dirname(__file__),
                'models',
                'best.pt'
            )
        
        # Vérifier que le modèle existe
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Modèle introuvable : {model_path}\n"
                f"Place ton fichier best.pt dans services/ml/models/"
            )
        
        print(f"🔄 Chargement du modèle depuis {model_path}...")
        
        # Charger le modèle (patch actif)
        self.model = YOLO(model_path)
        
        # Forcer CPU
        self.device = 'cpu'
        self.model.to(self.device)
        
        print(f"✅ Modèle chargé sur {self.device}")
        
        # Noms des classes
        self.class_names = {
            0: 'Bosse',
            1: 'Rayure',
            2: 'Fissure',
            3: 'Verre brisé',
            4: 'Lampe cassée',
            5: 'Pneu crevé'
        }
        
        # Couleurs pour les classes
        self.colors = {
            0: (255, 165, 0),   # Orange
            1: (135, 206, 235), # Bleu clair
            2: (255, 0, 0),     # Rouge
            3: (128, 0, 128),   # Violet
            4: (255, 255, 0),   # Jaune
            5: (220, 20, 60)    # Crimson
        }
    
    def detect(self, image_path, conf_threshold=0.25):
        """
        Détecte les dommages sur une image
        
        Args:
            image_path: Chemin vers l'image
            conf_threshold: Seuil de confiance
            
        Returns:
            dict: Résultats de la détection
        """
        print(f"🔍 Analyse de l'image : {image_path}")
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image introuvable : {image_path}")
        try:
            results = self.model.predict(
                source=image_path,
                conf=conf_threshold,
                device=self.device,
                verbose=False,
                save=False
            )
        except Exception as e:
            print(f"❌ Erreur pendant la prédiction : {e}")
            raise
        
        result = results[0]
        damages = []
        total_confidence = 0
        
        # Vérifier si on a des boxes (détection ou segmentation)
        if hasattr(result, 'boxes') and result.boxes is not None and len(result.boxes) > 0:
            print(f"📦 {len(result.boxes)} box(es) détectée(s)")
            
            for i, box in enumerate(result.boxes):
                try:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    bbox = box.xyxy[0].tolist()
                    
                    damage = {
                        'id': i,
                        'type': self.class_names.get(class_id, f'Classe {class_id}'),
                        'class_id': class_id,
                        'confidence': round(confidence * 100, 2),
                        'bbox': {
                            'x1': int(bbox[0]),
                            'y1': int(bbox[1]),
                            'x2': int(bbox[2]),
                            'y2': int(bbox[3])
                        },
                        'color': self.colors.get(class_id, (255, 255, 255))
                    }
                    
                    damages.append(damage)
                    total_confidence += confidence
                    print(f"  ✓ Dommage {i+1}: {damage['type']} ({damage['confidence']:.1f}%)")
                    
                except Exception as e:
                    print(f"  ⚠️ Erreur box {i}: {e}")
                    continue
        else:
            print("⚠️ Aucune box détectée")
        
        avg_confidence = (total_confidence / len(damages) * 100) if damages else 0
        
        print(f"✅ {len(damages)} dommage(s) détecté(s) au total")
        
        return {
            'total_damages': len(damages),
            'damages': damages,
            'avg_confidence': round(avg_confidence, 2),
            'image_size': result.orig_shape
        }
    
    def annotate_image(self, image_path, output_path, detection_results=None, conf_threshold=0.25):
        """
        Crée une image annotée avec les détections
        
        Args:
            image_path: Image originale
            output_path: Chemin de sortie
            detection_results: Résultats existants (optionnel)
            conf_threshold: Seuil de confiance
            
        Returns:
            str: Chemin de l'image annotée
        """
        print(f"🎨 Création de l'image annotée...")
        
        if detection_results is None:
            results = self.model.predict(
                source=image_path,
                conf=conf_threshold,
                device=self.device,
                verbose=False,
                save=False
            )
            result = results[0]
            annotated = result.plot()
        else:
            # Annoter manuellement
            image = cv2.imread(image_path)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            for damage in detection_results['damages']:
                bbox = damage['bbox']
                x1, y1, x2, y2 = bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2']
                color = damage['color']
                
                # Rectangle
                cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
                
                # Label
                label = f"{damage['type']} {damage['confidence']:.1f}%"
                font_scale = 0.6
                thickness = 2
                
                (text_width, text_height), _ = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
                )
                
                cv2.rectangle(
                    image,
                    (x1, y1 - text_height - 10),
                    (x1 + text_width, y1),
                    color,
                    -1
                )
                
                cv2.putText(
                    image,
                    label,
                    (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale,
                    (255, 255, 255),
                    thickness
                )
            
            annotated = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            cv2.imwrite(output_path, annotated)
            
            print(f"✅ Image annotée : {output_path}")
            return output_path
        
        # Utiliser plot() de YOLOv8
        annotated_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        Image.fromarray(annotated_rgb).save(output_path)
        
        print(f"✅ Image annotée : {output_path}")
        return output_path
    
    def estimate_cost(self, damages):
        """
        Estime le coût de réparation
        
        Args:
            damages: Liste des dommages
            
        Returns:
            dict: Estimation des coûts
        """
        cost_ranges = {
            'Bosse': (150, 400),
            'Rayure': (100, 300),
            'Fissure': (200, 600),
            'Verre brisé': (300, 800),
            'Lampe cassée': (150, 500),
            'Pneu crevé': (80, 200)
        }
        
        total_min = 0
        total_max = 0
        details = []
        
        for damage in damages:
            damage_type = damage['type']
            min_cost, max_cost = cost_ranges.get(damage_type, (100, 500))
            
            confidence_factor = damage['confidence'] / 100
            min_cost = int(min_cost * confidence_factor)
            max_cost = int(max_cost * confidence_factor)
            
            total_min += min_cost
            total_max += max_cost
            
            details.append({
                'type': damage_type,
                'cost_range': f"{min_cost}-{max_cost} DT"
            })
        
        return {
            'total_min': total_min,
            'total_max': total_max,
            'total_range': f"{total_min}-{total_max} DT",
            'details': details
        }