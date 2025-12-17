# advisor/vision/engine_detector.py
# Faster R-CNN ResNet50 FPN - Engine bay components detector
# Output: boxes + labels + scores

from __future__ import annotations

from typing import List, Dict, Optional

import torch
import torchvision
from torchvision.transforms import functional as F
from PIL import Image

CLASSES = [
    "Inverter Coolant Reservoir",
    "Battery",
    "Radiator Cap",
    "Windshield Wiper Fluid",
    "Fuse Box",
    "Power Steering Reservoir",
    "Brake Fluid",
    "Engine Oil Fill Cap",
    "Engine Oil Dip Stick",
    "Air Filter Cover",
    "ABS Unit",
    "Alternator",
    "Engine Coolant Reservoir",
    "Radiator",
    "Air Filter",
    "Engine Cover",
    "Cold Air Intake",
    "Clutch Fluid Reservoir",
    "Transmission Oil Dip Stick",
    "Intercooler Coolant Reservoir",
    "Oil Filter Housinig",
    "ATF Oil Reservoir",
    "Cabin Air Filter Housng",
    "Secondary Coolant Reservoir",
    "Electric Motor",
    "Oil Filter",
]

NUM_CLASSES = 26 + 1  # + background


def build_model():
    model = torchvision.models.detection.fasterrcnn_resnet50_fpn(weights=None)
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = torchvision.models.detection.faster_rcnn.FastRCNNPredictor(
        in_features, NUM_CLASSES
    )
    return model


class EngineBayDetector:
    def __init__(self, weights_path: str, device: Optional[str] = None):
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)

        self.model = build_model()
        state = torch.load(weights_path, map_location=self.device)
        self.model.load_state_dict(state)
        self.model.to(self.device)
        self.model.eval()

    @torch.no_grad()
    def predict(self, image: Image.Image, score_thresh: float = 0.5) -> List[Dict]:
        img_tensor = F.to_tensor(image).to(self.device)
        out = self.model([img_tensor])[0]

        boxes = out["boxes"].detach().cpu().tolist()
        labels = out["labels"].detach().cpu().tolist()
        scores = out["scores"].detach().cpu().tolist()

        results = []
        for box, lab, score in zip(boxes, labels, scores):
            if score < score_thresh:
                continue
            # labels are 1..26 (0 is background)
            cls_name = CLASSES[lab - 1]
            results.append({
                "name": cls_name,
                "label_id": lab - 1,            # 0..25
                "score": float(score),
                "box": [float(x) for x in box]  # [x1,y1,x2,y2]
            })

        return results
