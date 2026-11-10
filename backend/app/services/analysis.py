"""Diagnóstico rápido de la imagen: resolución, desenfoque, ruido, compresión y rostros."""
from __future__ import annotations

import cv2
import numpy as np


def _gray_small(rgb: np.ndarray, max_side: int = 768) -> np.ndarray:
    h, w = rgb.shape[:2]
    s = min(1.0, max_side / max(h, w))
    g = cv2.cvtColor((rgb * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    if s < 1.0:
        g = cv2.resize(g, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    return g


def estimate_noise(gray: np.ndarray) -> float:
    """Método de Immerkaer (sigma de ruido en escala 0-255)."""
    k = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], dtype=np.float32)
    h, w = gray.shape
    if h < 4 or w < 4:
        return 0.0
    conv = cv2.filter2D(gray.astype(np.float32), -1, k)[1:-1, 1:-1]
    return float(np.sum(np.abs(conv)) * np.sqrt(0.5 * np.pi) / (6.0 * (w - 2) * (h - 2)))


def blockiness(gray: np.ndarray) -> float:
    """Ratio de gradiente en fronteras de bloque 8×8 frente al resto (>1.1 sugiere JPEG fuerte)."""
    g = gray.astype(np.float32)
    h, w = g.shape
    if w < 32 or h < 32:
        return 1.0
    dx = np.abs(np.diff(g, axis=1))
    cols = np.arange(dx.shape[1])
    on = dx[:, cols % 8 == 7].mean()
    off = dx[:, cols % 8 != 7].mean()
    return float(on / (off + 1e-6))


def analyze(rgb: np.ndarray, faces: int) -> dict:
    h, w = rgb.shape[:2]
    gray = _gray_small(rgb)
    sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    noise = estimate_noise(gray)
    block = blockiness(gray)
    luma = float(gray.mean() / 255.0)
    contrast = float(gray.std() / 255.0)
    long_side = max(h, w)

    resolution = "baja" if long_side < 900 else "media" if long_side < 2000 else "alta"
    blur = "alto" if sharp < 40 else "moderado" if sharp < 150 else "bajo"
    noise_level = "alto" if noise > 6 else "moderado" if noise > 2.5 else "bajo"
    compression = "fuerte" if block > 1.25 else "moderada" if block > 1.08 else "baja"
    exposure = "oscura" if luma < 0.3 else "clara" if luma > 0.7 else "normal"

    rec: list[str] = []
    if resolution == "baja":
        rec.append("Resolución baja: escalar ayudará, pero los detalles nuevos serán una reconstrucción aproximada.")
    if blur != "bajo":
        rec.append("Hay desenfoque: se recomienda nitidez moderada (evita la intensidad alta para no crear halos).")
    if noise_level != "bajo":
        rec.append("Se detecta ruido digital: activa la reducción de ruido.")
    if compression != "baja":
        rec.append("Parece muy comprimida (bloques JPEG): el modelo de superresolución también suaviza estos artefactos.")
    if exposure == "oscura":
        rec.append("La imagen está subexpuesta: la corrección de exposición levantará sombras.")
    if contrast < 0.12:
        rec.append("Contraste bajo: la corrección de tono puede darle más vida.")
    if faces:
        rec.append(f"Se detectaron {faces} rostro(s). La mejora facial con IA aún no está disponible; la superresolución general respeta los rasgos.")
    if not rec:
        rec.append("La imagen está en buen estado; una mejora suave es suficiente.")

    return {
        "width": w,
        "height": h,
        "megapixels": round(w * h / 1e6, 2),
        "resolution": resolution,
        "blur": blur,
        "noise": noise_level,
        "compression": compression,
        "exposure": exposure,
        "metrics": {"laplacian_var": round(sharp, 1), "noise_sigma": round(noise, 2), "blockiness": round(block, 3), "mean_luma": round(luma, 3), "contrast": round(contrast, 3)},
        "faces": faces,
        "recommendations": rec,
    }
