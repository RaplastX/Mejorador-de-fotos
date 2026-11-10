"""Corrección de ojos rojos: busca ojos dentro de los rostros detectados y neutraliza solo los píxeles rojos intensos."""
from __future__ import annotations

from typing import Sequence

import cv2
import numpy as np

_eye = None


def _cascade() -> cv2.CascadeClassifier:
    global _eye
    if _eye is None:
        _eye = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
    return _eye


def fix_red_eye(rgb: np.ndarray, face_boxes: Sequence[tuple[int, int, int, int]]) -> tuple[np.ndarray, int]:
    out = rgb.copy()
    gray = cv2.cvtColor((np.clip(rgb, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    fixed = 0
    for fx, fy, fw, fh in face_boxes:
        top = gray[fy : fy + int(fh * 0.65), fx : fx + fw]  # los ojos están en la mitad superior
        if top.size == 0:
            continue
        eyes = _cascade().detectMultiScale(top, 1.1, 4, minSize=(max(8, fw // 12), max(8, fw // 12)))
        for ex, ey, ew, eh in eyes:
            x0, y0 = fx + ex, fy + ey
            roi = out[y0 : y0 + eh, x0 : x0 + ew]
            r, g, b = roi[..., 0], roi[..., 1], roi[..., 2]
            red = (r > 0.35) & (r > 1.8 * np.maximum(g, b))
            if red.sum() < 4:
                continue
            m = cv2.GaussianBlur(red.astype(np.float32), (0, 0), 1.0)[..., None]
            neutral = np.dstack([(g + b) / 2 * 0.9] * 3)  # oscurece y quita el rojo, conserva el brillo del reflejo
            roi[:] = roi * (1 - m) + neutral * m
            fixed += 1
    return out, fixed
