"""Restauración de daños leves de fotos antiguas con técnicas clásicas (sin modelos generativos):
rayones finos (líneas largas casi verticales/horizontales) y polvo/manchas pequeñas, rellenados con inpainting de Telea.

Limitaciones: no detecta rayones diagonales largos ni daños grandes; un detalle real muy fino y largo (un cable,
una antena) puede confundirse con un rayón. Por eso la intensidad es ajustable y empieza moderada."""
from __future__ import annotations

import cv2
import numpy as np


def _u8(rgb: np.ndarray) -> np.ndarray:
    return (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)


def detect_damage(rgb: np.ndarray, strength: float) -> np.ndarray:
    """Devuelve máscara uint8 (255 = dañado)."""
    s = float(np.clip(strength, 0, 1))
    gray = cv2.cvtColor(_u8(rgb), cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    from ..services.analysis import estimate_noise

    sigma = estimate_noise(gray)  # los umbrales se adaptan al grano: en fotos ruidosas no se confunde grano con daño
    thr = int(round(max(38 - 18 * s, 4.0 * sigma)))  # más intensidad → umbral más bajo (pero siempre por encima del grano)
    long_len = max(25, int(min(h, w) * 0.06))
    mask = np.zeros_like(gray)
    for polarity in ("bright", "dark"):
        for orient in ("v", "h"):
            # el elemento ancho es PERPENDICULAR a la línea que se busca
            k_thin = (5, 1) if orient == "v" else (1, 5)
            k_long = (long_len, 1) if orient == "v" else (1, long_len)
            se_thin = cv2.getStructuringElement(cv2.MORPH_RECT, k_thin)
            if polarity == "bright":
                d = cv2.subtract(gray, cv2.morphologyEx(gray, cv2.MORPH_OPEN, se_thin))
            else:
                d = cv2.subtract(cv2.morphologyEx(gray, cv2.MORPH_CLOSE, se_thin), gray)
            cand = (d > thr).astype(np.uint8) * 255
            se_long = cv2.getStructuringElement(cv2.MORPH_RECT, (k_long[0], k_long[1]) if orient == "h" else (k_long[1], k_long[0]))
            lines = cv2.morphologyEx(cand, cv2.MORPH_OPEN, se_long)  # solo trazos largos
            mask |= lines
    # polvo y manchas pequeñas: píxeles que difieren mucho de la mediana local, en componentes pequeños
    med = cv2.medianBlur(gray, 5)
    diff = cv2.absdiff(gray, med)
    spots = (diff > int(round(max(52 - 22 * s, 5.0 * sigma)))).astype(np.uint8)
    # el polvo es un punto AISLADO sobre fondo liso: se descarta todo lo que toque un borde real de la imagen
    gx, gy = cv2.Sobel(med, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(med, cv2.CV_32F, 0, 1, ksize=3)
    edges = (cv2.magnitude(gx, gy) > 60).astype(np.uint8)
    spots[cv2.dilate(edges, np.ones((7, 7), np.uint8)) > 0] = 0
    n, lab, stats, _ = cv2.connectedComponentsWithStats(spots, connectivity=8)
    max_area = max(6, int(round(h * w * 4e-6 + 8)))
    small = np.isin(lab, np.where((stats[:, cv2.CC_STAT_AREA] <= max_area) & (stats[:, cv2.CC_STAT_AREA] >= 1))[0]) & (lab > 0)
    mask[small] = 255
    return cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)


def remove_damage(rgb: np.ndarray, strength: float) -> tuple[np.ndarray, float]:
    """Devuelve (imagen reparada, fracción de píxeles reparados)."""
    if strength <= 0.01:
        return rgb, 0.0
    mask = detect_damage(rgb, strength)
    frac = float((mask > 0).mean())
    if frac == 0 or frac > 0.06:  # más del 6 % ya no parecen rayones sino textura: no se toca nada
        return rgb, 0.0
    bgr = cv2.cvtColor(_u8(rgb), cv2.COLOR_RGB2BGR)
    fixed = cv2.inpaint(bgr, mask, 3, cv2.INPAINT_TELEA)
    return cv2.cvtColor(fixed, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0, frac
