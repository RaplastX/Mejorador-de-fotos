"""Rotación en múltiplos de 90°, enderezado (con recorte automático de bordes vacíos) y recorte proporcional."""
from __future__ import annotations

import math

import cv2
import numpy as np

from ..core.errors import AppError


def _inscribed_scale(w: int, h: int, angle_deg: float) -> float:
    """Factor (<=1) del mayor rectángulo con la misma proporción que cabe en la imagen rotada sin bordes vacíos."""
    a = abs(math.radians(angle_deg))
    if a < 1e-6:
        return 1.0
    c, s = math.cos(a), math.sin(a)
    # el rectángulo w'×h' (misma proporción) rotado debe caber en w×h
    k = min(w / (w * c + h * s), h / (w * s + h * c))
    return min(1.0, k)


def transform(rgb: np.ndarray, rotate: int = 0, angle: float = 0.0, crop: tuple[float, float, float, float] | None = None) -> np.ndarray:
    if rotate not in (0, 90, 180, 270):
        raise AppError("La rotación debe ser 0, 90, 180 o 270 grados.", 400, "bad_rotate")
    if not -45 <= angle <= 45:
        raise AppError("El enderezado admite entre -45° y 45°.", 400, "bad_angle")
    out = rgb
    if rotate:
        out = np.rot90(out, k={90: -1, 180: 2, 270: 1}[rotate])  # sentido horario
    out = np.ascontiguousarray(out)
    if abs(angle) > 1e-3:
        h, w = out.shape[:2]
        m = cv2.getRotationMatrix2D((w / 2, h / 2), -angle, 1.0)  # ángulo positivo = giro horario
        rot = cv2.warpAffine(out, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
        k = _inscribed_scale(w, h, angle)
        nw, nh = max(1, int(w * k)), max(1, int(h * k))
        x0, y0 = (w - nw) // 2, (h - nh) // 2
        out = np.ascontiguousarray(rot[y0 : y0 + nh, x0 : x0 + nw])
    if crop is not None:
        cx, cy, cw, ch = crop
        if not (0 <= cx < 1 and 0 <= cy < 1 and 0 < cw <= 1 and 0 < ch <= 1 and cx + cw <= 1.0001 and cy + ch <= 1.0001):
            raise AppError("El recorte queda fuera de la imagen.", 400, "bad_crop")
        h, w = out.shape[:2]
        x0, y0 = int(round(cx * w)), int(round(cy * h))
        x1, y1 = min(w, x0 + max(1, int(round(cw * w)))), min(h, y0 + max(1, int(round(ch * h))))
        out = np.ascontiguousarray(out[y0:y1, x0:x1])
    return np.clip(out, 0, 1).astype(np.float32)
