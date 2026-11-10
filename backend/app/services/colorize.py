"""Colorización con DDColor (paper_tiny). Generativa: los colores son una suposición plausible, no un dato recuperado.
Se conserva la luminancia ORIGINAL a resolución completa y solo se añaden los canales de color (a, b)."""
from __future__ import annotations

import threading

import cv2
import numpy as np
import torch
import torch.nn.functional as F

from ..core.errors import AppError
from ..models.ddcolor_arch.ddcolor_arch import DDColor
from ..models.registry import MODELS, model_path, sha256_of
from ..models.upscaler import pick_device

_lock = threading.Lock()
_inst = None
KEY = "ddcolor-paper-tiny"
SIZE = 512


def available() -> bool:
    return model_path(KEY).is_file()


class Colorizer:
    def __init__(self) -> None:
        p = model_path(KEY)
        if not p.is_file():
            raise AppError("Falta el modelo de colorización. Ejecuta scripts/descargar_modelos.sh.", 503, "model_missing")
        if sha256_of(p) != MODELS[KEY].sha256:
            raise AppError("El modelo de colorización no coincide con su checksum; vuelve a descargarlo.", 503, "model_corrupt")
        self.device = pick_device()
        net = DDColor(encoder_name="convnext-t", decoder_name="MultiScaleColorDecoder", input_size=[SIZE, SIZE],
                      num_output_channels=2, last_norm="Spectral", do_normalize=False, num_queries=100, num_scales=3, dec_layers=9)
        st = torch.load(p, map_location="cpu", weights_only=True)
        net.load_state_dict(st["params"] if "params" in st else st, strict=False)  # head_cls no se usa
        self.net = net.eval().to(self.device)

    @torch.inference_mode()
    def colorize(self, rgb: np.ndarray, strength: float = 1.0) -> np.ndarray:
        """rgb float32 [0,1] → rgb colorizado. strength mezcla el color generado con el original (1 = completo)."""
        h, w = rgb.shape[:2]
        bgr = cv2.cvtColor(np.clip(rgb, 0, 1), cv2.COLOR_RGB2BGR)
        orig_l = cv2.cvtColor(bgr, cv2.COLOR_BGR2Lab)[:, :, :1]
        small = cv2.resize(bgr, (SIZE, SIZE))
        l_small = cv2.cvtColor(small, cv2.COLOR_BGR2Lab)[:, :, :1]
        gray_lab = np.concatenate((l_small, np.zeros_like(l_small), np.zeros_like(l_small)), axis=-1)
        gray_rgb = cv2.cvtColor(gray_lab, cv2.COLOR_LAB2RGB)
        t = torch.from_numpy(gray_rgb.transpose((2, 0, 1))).float().unsqueeze(0).to(self.device)
        ab = self.net(t).cpu()
        ab = F.interpolate(ab, size=(h, w), mode="bilinear", align_corners=False)[0].float().numpy().transpose(1, 2, 0)
        ab = ab * float(np.clip(strength, 0, 1))
        out = cv2.cvtColor(np.concatenate((orig_l, ab), axis=-1), cv2.COLOR_LAB2BGR)
        return np.clip(cv2.cvtColor(out, cv2.COLOR_BGR2RGB), 0, 1).astype(np.float32)


def get_colorizer() -> Colorizer:
    global _inst
    with _lock:
        if _inst is None:
            _inst = Colorizer()
        return _inst
