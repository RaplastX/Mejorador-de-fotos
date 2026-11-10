"""Pipeline completo de mejora: denoise → color → superresolución → remuestreo → nitidez."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import cv2
import numpy as np

from ..core.config import settings
from ..core.errors import AppError, Cancelled
from ..models.upscaler import get_upscaler
from . import basic

INTENSITY = {  # presets: (denoise, color, sharpen)
    "suave": (0.25, 0.35, 0.25),
    "equilibrada": (0.5, 0.6, 0.5),
    "intensa": (0.8, 0.85, 0.8),
}
TARGET_LONG_SIDE = {"1080p": 1920, "2k": 2560, "4k": 3840}


@dataclass
class Options:
    intensity: str = "equilibrada"
    denoise: Optional[float] = None  # 0..1, None = según preset
    color: Optional[float] = None
    sharpen: Optional[float] = None
    upscale: bool = True
    target: str = "original"  # original | 1080p | 2k | 4k
    scale: float = 2.0  # usado cuando target == original (x1, x2, x4)
    allow_downscale: bool = False

    def resolved(self) -> tuple[float, float, float]:
        d, c, s = INTENSITY.get(self.intensity, INTENSITY["equilibrada"])
        return (
            d if self.denoise is None else self.denoise,
            c if self.color is None else self.color,
            s if self.sharpen is None else self.sharpen,
        )


def plan_output(width: int, height: int, opts: Options) -> dict:
    """Calcula tamaño final y advertencias SIN procesar (la UI lo muestra antes de lanzar)."""
    long_side = max(width, height)
    warnings: list[str] = []
    if not opts.upscale:
        factor = 1.0
    elif opts.target in TARGET_LONG_SIDE:
        factor = TARGET_LONG_SIDE[opts.target] / long_side
        if factor < 1.0 and not opts.allow_downscale:
            factor = 1.0
            warnings.append("La imagen ya es más grande que el objetivo elegido; se mantiene el tamaño original.")
    else:
        factor = float(opts.scale)
    if factor < 1.0:
        factor = 1.0 if not opts.allow_downscale else factor
    out_w, out_h = max(1, round(width * factor)), max(1, round(height * factor))
    generative = factor > 1.0
    if factor > 4.0:
        warnings.append("El factor supera 4×: se aplica 4× con IA y el resto con interpolación; el detalle extra no es real.")
    if generative and long_side < 600 and factor >= 3:
        warnings.append("La imagen original es muy pequeña: el resultado a gran resolución reconstruye detalles de forma aproximada.")
    if generative:
        warnings.append("El escalado con IA reconstruye detalle plausible; no recupera información que no existía en la foto original.")
    if out_w * out_h > settings.max_output_pixels:
        raise AppError(
            f"El resultado ({out_w}×{out_h}) supera el límite configurado de {settings.max_output_pixels // 1_000_000} MP. "
            "Elige un objetivo menor o aumenta LUMA_MAX_OUTPUT_PIXELS.",
            400,
            "output_too_large",
        )
    return {"factor": round(factor, 4), "width": out_w, "height": out_h, "generative": generative, "warnings": warnings}


def run(
    rgb: np.ndarray,
    opts: Options,
    progress: Callable[[float, str], None],
    cancelled: Callable[[], bool],
) -> np.ndarray:
    h, w = rgb.shape[:2]
    plan = plan_output(w, h, opts)
    dn, col, shp = opts.resolved()
    img = rgb

    def check():
        if cancelled():
            raise Cancelled()

    progress(0.02, "Reduciendo ruido")
    # Si habrá superresolución, el modelo ya suaviza ruido: se aplica denoise más ligero para no perder detalle.
    img = basic.denoise(img, dn * (0.6 if plan["factor"] > 1.0 else 1.0))
    check()
    progress(0.10, "Corrigiendo exposición y color")
    img = basic.auto_color(img, col)
    check()

    factor = plan["factor"]
    if factor > 1.0:
        up = get_upscaler()
        progress(0.15, "Superresolución con IA")
        img = up.upscale(
            img,
            progress=lambda p: progress(0.15 + 0.75 * p, "Superresolución con IA"),
            cancelled=cancelled,
        )
        check()
        tw, th = plan["width"], plan["height"]
        if (img.shape[1], img.shape[0]) != (tw, th):
            progress(0.92, "Ajustando tamaño final")
            interp = cv2.INTER_AREA if (tw < img.shape[1]) else cv2.INTER_CUBIC
            img = cv2.resize(img, (tw, th), interpolation=interp)
        # Tras la SR ya hay nitidez; se aplica un refuerzo menor para no crear halos.
        shp *= 0.5
    progress(0.95, "Afinando nitidez")
    img = basic.sharpen(img, shp)
    progress(1.0, "Listo")
    return np.clip(img, 0, 1).astype(np.float32)
