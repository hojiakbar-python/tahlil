"""Lung X-ray classifier with Grad-CAM heatmap support."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np
import torch
import torchxrayvision as xrv
from PIL import Image
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
from skimage.transform import resize


DISEASE_LABELS = {
    "tuberkulyoz": "Oʻpka tuberkulyozi",
    "pnevmoniya": "Oʻpka pnevmoniyasi",
    "pnevmotoraks": "Oʻpka pnevmotoraksi",
}


@dataclass
class Prediction:
    tuberkulyoz: float
    pnevmoniya: float
    pnevmotoraks: float
    heatmap: np.ndarray | None = None
    raw_scores: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, float]:
        return {
            DISEASE_LABELS["tuberkulyoz"]: self.tuberkulyoz,
            DISEASE_LABELS["pnevmoniya"]: self.pnevmoniya,
            DISEASE_LABELS["pnevmotoraks"]: self.pnevmotoraks,
        }


class XRayClassifier:
    TB_PROXY_PATHOLOGIES = ("Consolidation", "Infiltration", "Lung Opacity")

    def __init__(self, device: str | None = None) -> None:
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._model: xrv.models.DenseNet | None = None
        self._cam: GradCAM | None = None

    def load(self) -> None:
        if self._model is not None:
            return
        model = xrv.models.DenseNet(weights="densenet121-res224-all")
        model.train(False)
        model.to(self.device)
        self._model = model
        target_layer = model.features.denseblock4
        self._cam = GradCAM(model=model, target_layers=[target_layer])

    @staticmethod
    def _to_xrv_array(image: Image.Image) -> np.ndarray:
        arr = np.array(image.convert("L"), dtype=np.float32)
        arr = xrv.datasets.normalize(arr, 255)
        arr = arr[None, ...]
        arr = resize(arr, (1, 224, 224), preserve_range=True).astype(np.float32)
        return arr

    def predict(self, image: Image.Image, with_heatmap: bool = True) -> Prediction:
        if self._model is None:
            self.load()

        arr = self._to_xrv_array(image)
        x = torch.from_numpy(arr).unsqueeze(0).to(self.device)

        with torch.no_grad():
            out = self._model(x).cpu().numpy()[0]

        pathologies = self._model.pathologies
        scores = {p: float(s) for p, s in zip(pathologies, out) if p}

        pnevmoniya = scores.get("Pneumonia", 0.0)
        pnevmotoraks = scores.get("Pneumothorax", 0.0)
        # Average several TB-related radiographic findings instead of max() —
        # single elevated channel (often Infiltration) caused false positives
        # on clean chest X-rays.
        tb_values = [scores.get(p, 0.0) for p in self.TB_PROXY_PATHOLOGIES]
        tuberkulyoz = sum(tb_values) / len(tb_values) if tb_values else 0.0

        heatmap = None
        if with_heatmap:
            heatmap = self._compute_heatmap(arr, scores)

        return Prediction(
            tuberkulyoz=float(tuberkulyoz),
            pnevmoniya=float(pnevmoniya),
            pnevmotoraks=float(pnevmotoraks),
            heatmap=heatmap,
            raw_scores=scores,
        )

    def _compute_heatmap(self, arr: np.ndarray, scores: dict[str, float]) -> np.ndarray | None:
        if self._cam is None:
            return None
        candidates = {
            "Pneumonia": scores.get("Pneumonia", 0.0),
            "Pneumothorax": scores.get("Pneumothorax", 0.0),
            "Consolidation": scores.get("Consolidation", 0.0),
            "Infiltration": scores.get("Infiltration", 0.0),
            "Lung Opacity": scores.get("Lung Opacity", 0.0),
        }
        target_name = max(candidates, key=candidates.get)
        target_idx = next(
            (i for i, p in enumerate(self._model.pathologies) if p == target_name),
            None,
        )
        if target_idx is None:
            return None
        try:
            x = torch.from_numpy(arr).unsqueeze(0).to(self.device)
            grayscale_cam = self._cam(
                input_tensor=x,
                targets=[ClassifierOutputTarget(target_idx)],
            )[0]
        except Exception:
            return None
        return grayscale_cam


def overlay_heatmap(image: Image.Image, heatmap: np.ndarray, alpha: float = 0.45) -> Image.Image:
    base = np.array(image.convert("RGB"))
    h, w = base.shape[:2]
    hm = cv2.resize(heatmap, (w, h))
    hm = np.clip(hm, 0, 1)
    hm_uint8 = (hm * 255).astype(np.uint8)
    colored = cv2.applyColorMap(hm_uint8, cv2.COLORMAP_JET)
    colored = cv2.cvtColor(colored, cv2.COLOR_BGR2RGB)
    blended = (base.astype(np.float32) * (1 - alpha) + colored.astype(np.float32) * alpha).astype(np.uint8)
    return Image.fromarray(blended)


def load_image(path: str | Path) -> Image.Image:
    return Image.open(path).convert("RGB")
