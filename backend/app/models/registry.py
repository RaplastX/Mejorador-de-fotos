"""Catálogo de modelos: fuente oficial, licencia y checksum. Los pesos NO se redistribuyen en el repo."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from ..core.config import settings


@dataclass(frozen=True)
class ModelInfo:
    key: str
    title: str
    filename: str
    url: str
    sha256: str
    code_license: str
    weights_license: str
    source: str
    purpose: str


MODELS: dict[str, ModelInfo] = {
    "realesr-general-x4v3": ModelInfo(
        key="realesr-general-x4v3",
        title="Real-ESRGAN general x4 v3 (compacto)",
        filename="realesr-general-x4v3.pth",
        url="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth",
        sha256="8dc7edb9ac80ccdc30c3a5dca6616509367f05fbc184ad95b731f05bece96292",
        code_license="BSD-3-Clause",
        weights_license="Publicados en el repositorio oficial bajo BSD-3-Clause (sin licencia de pesos separada)",
        source="https://github.com/xinntao/Real-ESRGAN",
        purpose="Superresolución x4 y reducción de ruido/artefactos (CPU y GPU)",
    ),
}


def model_path(key: str) -> Path:
    return settings.models_dir / MODELS[key].filename


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def model_status(key: str, verify: bool = False) -> dict:
    info = MODELS[key]
    path = model_path(key)
    present = path.is_file()
    ok = None
    if present and verify:
        ok = sha256_of(path) == info.sha256
    return {
        "key": key,
        "title": info.title,
        "present": present,
        "checksum_ok": ok,
        "code_license": info.code_license,
        "weights_license": info.weights_license,
        "source": info.source,
        "download_url": info.url,
        "purpose": info.purpose,
    }
