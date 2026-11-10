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
    "realesrgan-x4plus": ModelInfo(
        key="realesrgan-x4plus",
        title="Real-ESRGAN x4plus (calidad alta, lento)",
        filename="RealESRGAN_x4plus.pth",
        url="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
        sha256="4fa0d38905f75ac06eb49a7951b426670021be3018265fd191d2125df9d682f1",
        code_license="BSD-3-Clause",
        weights_license="Release oficial del repo BSD-3-Clause; sin licencia de pesos separada visible",
        source="https://github.com/xinntao/Real-ESRGAN",
        purpose="Superresolución x4 de mayor calidad (mejor con desenfoque); mucho más lento en CPU",
    ),
    "ddcolor-paper-tiny": ModelInfo(
        key="ddcolor-paper-tiny",
        title="DDColor paper_tiny (colorización)",
        filename="ddcolor_paper_tiny.pth",
        url="https://huggingface.co/piddnad/DDColor-models/resolve/main/ddcolor_paper_tiny.pth",
        sha256="81dd643904f4664c3718513e3320ae3db0c567f0d3e18398606659adee7bfc17",
        code_license="Apache-2.0 (piddnad/DDColor)",
        weights_license="Apache-2.0 según la ficha oficial en Hugging Face (piddnad/DDColor-models)",
        source="https://github.com/piddnad/DDColor",
        purpose="Colorización de fotos en blanco y negro (generativa: los colores son una suposición plausible)",
    ),
    "lama-big": ModelInfo(
        key="lama-big",
        title="LaMa big-lama (borrar objetos / inpainting, TorchScript)",
        filename="big-lama.pt",
        url="https://github.com/Sanster/models/releases/download/add_big_lama/big-lama.pt",
        sha256="344c77bbcb158f17dd143070d1e789f38a66c04202311ae3a258ef66667a9ea9",
        code_license="Apache-2.0 (advimman/lama)",
        weights_license="Pesos de LaMa reempaquetados en TorchScript por Sanster/IOPaint (Apache-2.0); licencia de pesos original: no verificada por separado",
        source="https://github.com/advimman/lama",
        purpose="Rellena con contenido plausible el área marcada para borrar un objeto",
    ),
    "gfpgan-v1.4": ModelInfo(
        key="gfpgan-v1.4",
        title="GFPGAN v1.4 (restauración facial)",
        filename="GFPGANv1.4.pth",
        url="https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth",
        sha256="e2cd4703ab14f4d01fd1383a8a8b266f9a5833dacee8e6a79d3bf21a1b6be5ad",
        code_license="Apache-2.0 (TencentARC/GFPGAN)",
        weights_license="Publicados en el release oficial del repo Apache-2.0; sin licencia de pesos separada visible. Entrenados con FFHQ (términos del dataset: no verificados)",
        source="https://github.com/TencentARC/GFPGAN",
        purpose="Restauración de rostros (reconstruye detalle facial; mezcla ajustable con el rostro original)",
    ),
    "retinaface-resnet50": ModelInfo(
        key="retinaface-resnet50",
        title="RetinaFace ResNet50 (detección y alineado de rostros)",
        filename="detection_Resnet50_Final.pth",
        url="https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth",
        sha256="6d1de9c2944f2ccddca5f5e010ea5ae64a39845a86311af6fdf30841b0a5a16d",
        code_license="MIT (xinntao/facexlib)",
        weights_license="Release oficial de facexlib; sin licencia de pesos separada visible",
        source="https://github.com/xinntao/facexlib",
        purpose="Localiza rostros y 5 puntos para alinear; no guarda plantillas ni identifica personas",
    ),
    "parsing-parsenet": ModelInfo(
        key="parsing-parsenet",
        title="ParseNet (segmentación facial, requerido por facexlib)",
        filename="parsing_parsenet.pth",
        url="https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth",
        sha256="3d558d8d0e42c20224f13cf5a29c79eba2d59913419f945545d8cf7b72920de2",
        code_license="MIT (xinntao/facexlib)",
        weights_license="Release oficial de facexlib; sin licencia de pesos separada visible",
        source="https://github.com/xinntao/facexlib",
        purpose="facexlib lo carga siempre al preparar el restaurador; no se usa para identificar personas",
    ),
}

# Los SHA-256 de GFPGAN, RetinaFace y ParseNet se fijaron a partir de la primera descarga oficial (upstream no publica checksums).


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
