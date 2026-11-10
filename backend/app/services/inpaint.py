"""Borrar objetos con LaMa (big-lama, TorchScript). Procesa solo un recorte alrededor de la máscara (con contexto) y
vuelve a pegar únicamente la zona marcada, de modo que el resto de la foto no se modifica ni un píxel."""
from __future__ import annotations

import threading

import cv2
import numpy as np
import torch

from ..core.errors import AppError
from ..models.registry import MODELS, model_path, sha256_of
from ..models.upscaler import pick_device

KEY = "lama-big"
_lock = threading.Lock()
_inst = None
MAX_SIDE = 1024  # los recortes mayores se reducen para el modelo y la zona rellenada se devuelve a su tamaño


def available() -> bool:
    return model_path(KEY).is_file()


class Inpainter:
    def __init__(self) -> None:
        p = model_path(KEY)
        if not p.is_file():
            raise AppError("Falta el modelo para borrar objetos. Ejecuta scripts/descargar_modelos.sh.", 503, "model_missing")
        if sha256_of(p) != MODELS[KEY].sha256:
            raise AppError("El modelo para borrar objetos no coincide con su checksum; vuelve a descargarlo.", 503, "model_corrupt")
        self.device = pick_device()
        self.net = torch.jit.load(str(p), map_location=self.device).eval()

    @torch.inference_mode()
    def _run(self, img: np.ndarray, mask: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        ph, pw = (-h) % 8, (-w) % 8
        img_p = np.pad(img, ((0, ph), (0, pw), (0, 0)), mode="symmetric")
        mask_p = np.pad(mask, ((0, ph), (0, pw)), mode="symmetric")
        ti = torch.from_numpy(img_p.transpose(2, 0, 1)).unsqueeze(0).float().to(self.device)
        tm = torch.from_numpy((mask_p > 0.5).astype(np.float32))[None, None].to(self.device)
        out = self.net(ti, tm)[0].permute(1, 2, 0).cpu().numpy()
        return np.clip(out[:h, :w], 0, 1)

    def remove(self, rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """rgb float32 [0,1]; mask bool/uint8 (verdadero = borrar), mismo tamaño. Devuelve rgb sin el objeto."""
        h, w = rgb.shape[:2]
        m = (mask > 0).astype(np.uint8)
        if m.sum() == 0:
            raise AppError("Marca con el pincel el objeto que quieres borrar.", 400, "empty_mask")
        m = cv2.dilate(m, np.ones((5, 5), np.uint8))  # margen para no dejar un borde del objeto
        ys, xs = np.where(m > 0)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        margin = max(64, int(max(y1 - y0, x1 - x0) * 0.6))  # contexto alrededor
        cy0, cy1, cx0, cx1 = max(0, y0 - margin), min(h, y1 + margin), max(0, x0 - margin), min(w, x1 + margin)
        crop, cm = rgb[cy0:cy1, cx0:cx1], m[cy0:cy1, cx0:cx1].astype(np.float32)
        ch, cw = crop.shape[:2]
        s = min(1.0, MAX_SIDE / max(ch, cw))
        if s < 1.0:
            small = cv2.resize(crop, (max(8, int(cw * s)), max(8, int(ch * s))), interpolation=cv2.INTER_AREA)
            sm = cv2.resize(cm, (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST)
            res = cv2.resize(self._run(small, sm), (cw, ch), interpolation=cv2.INTER_CUBIC)
        else:
            res = self._run(crop, cm)
        feather = cv2.GaussianBlur(cm, (0, 0), 2.0)[..., None]  # borde suave; fuera de la máscara no cambia nada
        feather = np.where(cm[..., None] > 0, 1.0, feather * (cv2.dilate(cm, np.ones((9, 9), np.uint8))[..., None] > 0))
        out = rgb.copy()
        out[cy0:cy1, cx0:cx1] = crop * (1 - feather) + np.clip(res, 0, 1) * feather
        return out.astype(np.float32)


def get_inpainter() -> Inpainter:
    global _inst
    with _lock:
        if _inst is None:
            _inst = Inpainter()
        return _inst
