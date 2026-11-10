"""Superresolución x4 con mosaicos solapados (tiling) sobre CPU o CUDA."""
from __future__ import annotations

import threading
from typing import Callable, Optional

import numpy as np
import torch

from ..core.config import settings
from ..core.errors import AppError, Cancelled
from .registry import MODELS, model_path, sha256_of
from .rrdbnet import RRDBNet
from .srvgg import SRVGGNetCompact

_lock = threading.Lock()
_cache: dict[str, "Upscaler"] = {}


def pick_device() -> torch.device:
    pref = settings.device_preference
    if pref == "cpu":
        return torch.device("cpu")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def hardware_info() -> dict:
    dev = pick_device()
    info = {
        "device": dev.type,
        "torch": torch.__version__,
        "threads": torch.get_num_threads(),
        "gpu_name": None,
        "vram_gb": None,
    }
    if dev.type == "cuda":
        props = torch.cuda.get_device_properties(0)
        info["gpu_name"] = props.name
        info["vram_gb"] = round(props.total_memory / 1024**3, 1)
    return info


class Upscaler:
    scale = 4

    def __init__(self, key: str = "realesr-general-x4v3"):
        path = model_path(key)
        if not path.is_file():
            raise AppError(
                "Falta el modelo de superresolución. Ejecuta scripts/descargar_modelos.sh "
                "(descarga oficial desde GitHub, ~5 MB).",
                status=503,
                code="model_missing",
            )
        if sha256_of(path) != MODELS[key].sha256:
            raise AppError("El archivo del modelo no coincide con el checksum oficial; vuelve a descargarlo.", 503, "model_corrupt")
        if settings.torch_threads > 0:
            torch.set_num_threads(settings.torch_threads)
        self.device = pick_device()
        if key == "realesrgan-x4plus":
            net = RRDBNet(3, 3, num_feat=64, num_block=23, num_grow_ch=32)
        else:
            net = SRVGGNetCompact(3, 3, num_feat=64, num_conv=32, upscale=4, act_type="prelu")
        state = torch.load(path, map_location="cpu", weights_only=True)
        net.load_state_dict(state["params_ema"] if "params_ema" in state else state["params"] if "params" in state else state, strict=True)
        self.net = net.eval().to(self.device)

    @torch.inference_mode()
    def _run(self, tile: np.ndarray) -> np.ndarray:
        t = torch.from_numpy(tile).permute(2, 0, 1).unsqueeze(0).to(self.device)
        out = self.net(t).clamp_(0, 1)
        return out.squeeze(0).permute(1, 2, 0).cpu().numpy()

    def upscale(
        self,
        img: np.ndarray,
        progress: Optional[Callable[[float], None]] = None,
        cancelled: Optional[Callable[[], bool]] = None,
        tile: Optional[int] = None,
        overlap: Optional[int] = None,
    ) -> np.ndarray:
        """img: float32 RGB [0,1], HxWx3 → float32 RGB [0,1], 4H x 4W."""
        tile = tile or settings.tile_size
        pad = overlap if overlap is not None else settings.tile_overlap
        h, w, _ = img.shape
        s = self.scale
        out = np.zeros((h * s, w * s, 3), dtype=np.float32)
        ys = list(range(0, h, tile))
        xs = list(range(0, w, tile))
        total = len(ys) * len(xs)
        done = 0
        for y0 in ys:
            for x0 in xs:
                if cancelled and cancelled():
                    raise Cancelled()
                y1, x1 = min(y0 + tile, h), min(x0 + tile, w)
                py0, px0 = max(y0 - pad, 0), max(x0 - pad, 0)
                py1, px1 = min(y1 + pad, h), min(x1 + pad, w)
                res = self._run(np.ascontiguousarray(img[py0:py1, px0:px1]))
                cy0, cx0 = (y0 - py0) * s, (x0 - px0) * s
                out[y0 * s : y1 * s, x0 * s : x1 * s] = res[cy0 : cy0 + (y1 - y0) * s, cx0 : cx0 + (x1 - x0) * s]
                done += 1
                if progress:
                    progress(done / total)
        return out


def get_upscaler(key: str = "realesr-general-x4v3") -> Upscaler:
    with _lock:
        if key not in _cache:
            _cache[key] = Upscaler(key)
        return _cache[key]
