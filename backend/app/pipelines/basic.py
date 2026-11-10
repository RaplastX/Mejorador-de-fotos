"""Correcciones clásicas (OpenCV/NumPy): denoise, exposición/color y nitidez moderada."""
from __future__ import annotations

import cv2
import numpy as np


def _u8(a: np.ndarray) -> np.ndarray:
    return (np.clip(a, 0, 1) * 255.0 + 0.5).astype(np.uint8)


def denoise(rgb: np.ndarray, strength: float) -> np.ndarray:
    """Denoise de luminancia (fuerte) y crominancia (más fuerte) con NLM. strength 0..1."""
    if strength <= 0.01:
        return rgb
    ycc = cv2.cvtColor(_u8(rgb), cv2.COLOR_RGB2YCrCb)
    y, cr, cb = cv2.split(ycc)
    h_luma = 2.0 + 8.0 * strength
    h_chroma = 3.0 + 9.0 * strength
    y = cv2.fastNlMeansDenoising(y, None, h_luma, 5, 15)
    cr = cv2.fastNlMeansDenoising(cr, None, h_chroma, 5, 15)
    cb = cv2.fastNlMeansDenoising(cb, None, h_chroma, 5, 15)
    out = cv2.cvtColor(cv2.merge([y, cr, cb]), cv2.COLOR_YCrCb2RGB).astype(np.float32) / 255.0
    return out


def auto_color(rgb: np.ndarray, strength: float, white_balance: bool = True) -> np.ndarray:
    """Exposición (gamma hacia luminancia objetivo), contraste local suave (CLAHE en L), balance gris-mundo limitado."""
    if strength <= 0.01:
        return rgb
    out = rgb.copy()
    if white_balance:
        means = out.reshape(-1, 3).mean(axis=0) + 1e-6
        gain = means.mean() / means
        lim = 1.0 + 0.10 * strength
        gain = np.clip(gain, 1.0 / lim, lim)
        out = np.clip(out * ((1 - 0.7 * strength) + 0.7 * strength * gain), 0, 1)
    # exposición: gamma hacia luminancia media ~0.45, limitada
    luma = float(out.mean())
    if luma > 1e-3:
        gamma = np.log(0.45) / np.log(np.clip(luma, 0.05, 0.95))
        gamma = float(np.clip(gamma, 0.65, 1.5))
        gamma = 1.0 + (gamma - 1.0) * strength * 0.8
        out = np.power(np.clip(out, 1e-6, 1), gamma)
    lab = cv2.cvtColor(_u8(out), cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=1.0 + 1.6 * strength, tileGridSize=(8, 8))
    l2 = clahe.apply(l)
    l = cv2.addWeighted(l, 1 - 0.6 * strength, l2, 0.6 * strength, 0)
    out = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2RGB).astype(np.float32) / 255.0
    # saturación ligera
    hsv = cv2.cvtColor(_u8(out), cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * (1.0 + 0.10 * strength), 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32) / 255.0


def sharpen(rgb: np.ndarray, strength: float, radius: float = 1.2) -> np.ndarray:
    """Máscara de enfoque solo en luminancia, con umbral y recorte de sobreimpulso para evitar halos."""
    if strength <= 0.01:
        return rgb
    ycc = cv2.cvtColor(_u8(rgb), cv2.COLOR_RGB2YCrCb).astype(np.float32) / 255.0
    y = ycc[..., 0]
    blur = cv2.GaussianBlur(y, (0, 0), radius)
    detail = y - blur
    detail = np.where(np.abs(detail) < 0.008, 0.0, detail)  # no amplifica ruido fino
    amount = 0.2 + 0.9 * strength
    sharp = y + amount * detail
    # limitar sobreimpulso respecto al entorno local (anti-halo)
    mx = cv2.dilate(y, np.ones((3, 3), np.uint8))
    mn = cv2.erode(y, np.ones((3, 3), np.uint8))
    margin = 0.04
    sharp = np.clip(sharp, mn - margin, mx + margin)
    ycc[..., 0] = np.clip(sharp, 0, 1)
    out = cv2.cvtColor((ycc * 255.0 + 0.5).astype(np.uint8), cv2.COLOR_YCrCb2RGB)
    return out.astype(np.float32) / 255.0
