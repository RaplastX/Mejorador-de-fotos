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
    "suave": (0.25, 0.25, 0.25),
    "equilibrada": (0.5, 0.4, 0.5),
    "intensa": (0.8, 0.75, 0.8),
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
    faces: bool = False
    face_strength: float = 0.7  # 0 = rostro original, 1 = restauración completa
    skin: bool = False
    skin_smooth: float = 0.35
    skin_wrinkles: float = 0.35
    keep_texture: bool = True
    exclude_faces: tuple = ()  # cajas (x, y, w, h) en coordenadas de la imagen ORIGINAL

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
    if opts.skin:
        warnings.append("El retoque de piel es edición clásica y subjetiva: úsalo con intensidad baja para conservar poros, lunares y rasgos. Solo actúa donde se detecta un rostro frontal.")
    if opts.faces:
        warnings.append("La restauración facial con IA reconstruye rasgos que no se distinguen en la foto; con intensidad alta puede alterar la expresión o parecer artificial. Baja la intensidad para conservar la identidad.")
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
    if opts.faces:
        from ..services import face_restore

        fr = face_restore.get_face_restorer()
        f = plan["factor"]
        excl = [(x * f, y * f, bw * f, bh * f) for x, y, bw, bh in opts.exclude_faces]
        progress(0.93, "Restaurando rostros")
        img, n = fr.restore(img, opts.face_strength, excl, lambda p: progress(0.93 + 0.05 * p, "Restaurando rostros"), cancelled)
        check()
        if n == 0:
            progress(0.98, "No se encontraron rostros que mejorar")
    if opts.skin:
        from ..services import faces as face_det
        from . import skin

        progress(0.985, "Retocando piel")
        f = plan["factor"]
        excl = [(x * f, y * f, bw * f, bh * f) for x, y, bw, bh in opts.exclude_faces]
        boxes = [b for b in face_det.detect_faces(img)
                 if not any(ex <= b[0] + b[2] / 2 <= ex + ew and ey <= b[1] + b[3] / 2 <= ey + eh for ex, ey, ew, eh in excl)]
        img = skin.retouch(img, boxes, opts.skin_smooth, opts.skin_wrinkles, opts.keep_texture)
    progress(0.99, "Afinando nitidez")
    img = basic.sharpen(img, shp)
    progress(1.0, "Listo")
    return np.clip(img, 0, 1).astype(np.float32)
