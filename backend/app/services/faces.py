"""Detección de rostros (solo cajas delimitadoras). No se guardan plantillas ni embeddings."""
from __future__ import annotations

import cv2
import numpy as np

_cascade = None


def _get_cascade() -> cv2.CascadeClassifier:
    global _cascade
    if _cascade is None:
        _cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    return _cascade


def detect_faces(rgb: np.ndarray, max_side: int = 960) -> list[tuple[int, int, int, int]]:
    """Devuelve cajas (x, y, w, h) en coordenadas de la imagen original."""
    h, w = rgb.shape[:2]
    s = min(1.0, max_side / max(h, w))
    gray = cv2.cvtColor((rgb * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    if s < 1.0:
        gray = cv2.resize(gray, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    gray = cv2.equalizeHist(gray)
    min_side = max(24, int(min(gray.shape) * 0.04))
    boxes = _get_cascade().detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(min_side, min_side))
    return [(int(x / s), int(y / s), int(bw / s), int(bh / s)) for (x, y, bw, bh) in boxes]
