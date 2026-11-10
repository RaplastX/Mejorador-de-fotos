"""Validación, lectura (con EXIF) y exportación segura de imágenes."""
from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from ..core.config import settings
from ..core.errors import AppError

Image.MAX_IMAGE_PIXELS = settings.max_input_pixels * 2  # aviso de PIL antes de nuestro límite duro

ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
EXPORT_FORMATS = {"jpeg": ("JPEG", "jpg"), "png": ("PNG", "png"), "webp": ("WEBP", "webp")}
GPS_IFD_TAG = 0x8825
ORIENTATION_TAG = 0x0112


def validate_and_open(data: bytes) -> Image.Image:
    """Comprueba el contenido real (no la extensión ni el MIME) y devuelve la imagen cargada."""
    if not data:
        raise AppError("El archivo está vacío.", 400, "empty")
    if len(data) > settings.max_upload_bytes:
        raise AppError(f"El archivo supera el límite de {settings.max_upload_bytes // (1024 * 1024)} MB.", 413, "too_large")
    try:
        probe = Image.open(io.BytesIO(data))
        fmt = probe.format
        probe.verify()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError, ValueError):
        raise AppError("El archivo no es una imagen válida (se admiten JPEG, PNG y WebP).", 415, "invalid_image")
    if fmt not in ALLOWED_FORMATS:
        raise AppError("Formato no admitido. Usa JPEG, PNG o WebP.", 415, "unsupported_format")
    img = Image.open(io.BytesIO(data))
    if img.width * img.height > settings.max_input_pixels:
        raise AppError(
            f"La imagen es demasiado grande ({img.width}×{img.height}). Máximo {settings.max_input_pixels // 1_000_000} megapíxeles.",
            413,
            "too_many_pixels",
        )
    try:
        img.load()
    except (OSError, ValueError, Image.DecompressionBombError):
        raise AppError("La imagen está dañada y no se pudo leer.", 415, "corrupt_image")
    return img


def to_working_array(img: Image.Image) -> tuple[np.ndarray, Optional[np.ndarray]]:
    """Aplica la orientación EXIF y devuelve RGB float32 [0,1] y alfa uint8 opcional."""
    img = ImageOps.exif_transpose(img)
    alpha = None
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        alpha = np.array(rgba.getchannel("A"))
        if alpha.min() == 255:
            alpha = None
    rgb = img.convert("RGB")
    return np.asarray(rgb, dtype=np.float32) / 255.0, alpha


def array_to_pil(arr: np.ndarray) -> Image.Image:
    return Image.fromarray((np.clip(arr, 0, 1) * 255.0 + 0.5).astype(np.uint8), "RGB")


def make_display_jpeg(img: Image.Image, max_side: int = 2048, quality: int = 88) -> bytes:
    """Versión para pantalla (nunca para exportar)."""
    im = img.copy()
    im.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=quality)
    return buf.getvalue()


_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_stem(name: str | None) -> str:
    stem = Path(name or "foto").stem
    stem = _SAFE.sub("_", stem).strip("._-")[:60]
    return stem or "foto"


def unique_name(stem: str, ext: str, taken: set[str]) -> str:
    cand = f"{stem}_mejorada.{ext}"
    i = 2
    while cand in taken:
        cand = f"{stem}_mejorada_{i}.{ext}"
        i += 1
    return cand


def export_image(
    img: Image.Image,
    fmt: str,
    quality: int = 92,
    keep_metadata: bool = False,
    keep_gps: bool = False,
    source_exif: Optional[Image.Exif] = None,
    alpha: Optional[np.ndarray] = None,
) -> bytes:
    if fmt not in EXPORT_FORMATS:
        raise AppError("Formato de salida no admitido.", 400, "bad_format")
    pil_fmt, _ = EXPORT_FORMATS[fmt]
    quality = int(min(max(quality, 40), 100))
    out = img
    if alpha is not None and pil_fmt in ("PNG", "WEBP"):
        a = Image.fromarray(alpha).resize(img.size, Image.LANCZOS)
        out = img.convert("RGBA")
        out.putalpha(a)
    kwargs: dict = {}
    if pil_fmt == "JPEG":
        kwargs.update(quality=quality, optimize=True, subsampling=0)
    elif pil_fmt == "WEBP":
        kwargs.update(quality=quality, method=4)
    elif pil_fmt == "PNG":
        kwargs.update(optimize=False, compress_level=6)
    if keep_metadata and source_exif is not None and pil_fmt in ("JPEG", "WEBP", "PNG"):
        exif = Image.Exif()
        for k, v in source_exif.items():
            if k in (GPS_IFD_TAG, ORIENTATION_TAG):
                continue
            exif[k] = v
        try:
            sub = source_exif.get_ifd(0x8769)
            if sub:
                exif_ifd = exif.get_ifd(0x8769)
                exif_ifd.update(sub)
        except Exception:
            pass
        if keep_gps:
            try:
                gps = source_exif.get_ifd(GPS_IFD_TAG)
                if gps:
                    exif.get_ifd(GPS_IFD_TAG).update(gps)
            except Exception:
                pass
        kwargs["exif"] = exif.tobytes()
    buf = io.BytesIO()
    if pil_fmt == "JPEG" and out.mode == "RGBA":
        out = out.convert("RGB")
    out.save(buf, pil_fmt, **kwargs)
    return buf.getvalue()
