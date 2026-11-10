"""Retoque natural de piel y arrugas (edición clásica, no generativa).

Separación de frecuencias dentro de una máscara de piel por rostro:
  base (color/iluminación, intacta) + media (arrugas, manchas) + fina (poros, textura).
- «arrugas» atenúa la banda media con un filtro que respeta bordes.
- «suavizado» atenúa la banda fina, pero «conservar textura» garantiza un mínimo para evitar piel de plástico.
No cambia el tono (la base no se toca), ni ojos, cejas ni labios (excluidos de la máscara).
"""
from __future__ import annotations

from typing import Sequence

import cv2
import numpy as np

Box = tuple[float, float, float, float]


def skin_mask(rgb: np.ndarray, box: Box) -> np.ndarray:
    """Máscara suave [0,1] de piel dentro de una elipse sobre el rostro, sin ojos/cejas/boca."""
    h, w = rgb.shape[:2]
    x, y, bw, bh = box
    cx, cy = x + bw / 2, y + bh * 0.55
    ell = np.zeros((h, w), np.float32)
    cv2.ellipse(ell, (int(cx), int(cy)), (max(1, int(bw * 0.52)), max(1, int(bh * 0.62))), 0, 0, 360, 1.0, -1)
    u8 = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
    ycc = cv2.cvtColor(u8, cv2.COLOR_RGB2YCrCb)
    cr, cb = ycc[..., 1].astype(np.int16), ycc[..., 2].astype(np.int16)
    skin = ((cr > 135) & (cr < 175) & (cb > 85) & (cb < 130)).astype(np.float32)
    # excluir rasgos oscuros y de alto contraste (ojos, cejas, pestañas, fosas nasales) y labios (Cr alto)
    gray = cv2.cvtColor(u8, cv2.COLOR_RGB2GRAY).astype(np.float32)
    local = cv2.GaussianBlur(gray, (0, 0), max(2.0, bw / 10))
    dark = (gray < local - 22).astype(np.float32)
    lips = (cr > 168).astype(np.float32)
    feat = cv2.dilate(np.clip(dark + lips, 0, 1), np.ones((max(3, int(bw / 30)) | 1,) * 2, np.uint8))
    m = ell * skin * (1.0 - feat)
    m = cv2.GaussianBlur(m, (0, 0), max(2.0, bw / 25))
    return np.clip(m, 0, 1)


def retouch(
    rgb: np.ndarray,
    boxes: Sequence[Box],
    smooth: float,
    wrinkles: float,
    keep_texture: bool = True,
) -> np.ndarray:
    if not boxes or (smooth <= 0.01 and wrinkles <= 0.01):
        return rgb
    out = rgb.copy()
    for box in boxes:
        x, y, bw, bh = (int(round(v)) for v in box)
        pad = int(bw * 0.4)
        x0, y0 = max(0, x - pad), max(0, y - pad)
        x1, y1 = min(rgb.shape[1], x + bw + pad), min(rgb.shape[0], y + bh + pad)
        roi = np.ascontiguousarray(out[y0:y1, x0:x1])
        local_box = (x - x0, y - y0, bw, bh)
        mask = skin_mask(roi, local_box)[..., None]
        s_fine = max(0.7, bw / 190.0)  # tamaños relativos al rostro (independientes de la resolución)
        b1 = cv2.GaussianBlur(roi, (0, 0), s_fine)
        b2 = cv2.GaussianBlur(roi, (0, 0), s_fine * 5)
        fine, mid, base = roi - b1, b1 - b2, b2
        # banda media con filtro de bordes: arrugas/manchas sin lavar contornos reales
        sigma_c = 0.04 + 0.06 * wrinkles
        mid_src = np.clip(b1, 0, 1).astype(np.float32)
        mid_s = cv2.bilateralFilter(mid_src, d=0, sigmaColor=sigma_c, sigmaSpace=max(2.0, s_fine * 4)) - b2
        k_w = np.clip(wrinkles, 0, 1) * 0.85
        mid_new = mid * (1 - k_w) + mid_s * k_w
        floor = 0.55 if keep_texture else 0.15  # fracción mínima de textura fina que se conserva
        fine_new = fine * (1 - (1 - floor) * np.clip(smooth, 0, 1))
        res = base + mid_new + fine_new
        out[y0:y1, x0:x1] = np.clip(roi * (1 - mask) + res * mask, 0, 1)
    return out
