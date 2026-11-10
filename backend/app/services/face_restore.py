"""Restauración facial con GFPGAN v1.4 (detección/alineado con RetinaFace de facexlib).

- Mezcla ajustable entre el rostro original y el restaurado (preserva identidad con valores bajos).
- Permite excluir rostros concretos. No se guardan embeddings ni plantillas faciales.
"""
from __future__ import annotations

import threading
from typing import Callable, Optional, Sequence

import cv2
import numpy as np
import torch

from ..core.config import settings
from ..core.errors import AppError, Cancelled
from ..models.gfpgan_arch.gfpganv1_clean_arch import GFPGANv1Clean
from ..models.registry import MODELS, model_path, sha256_of
from ..models.upscaler import pick_device

FACE_MODELS = ("gfpgan-v1.4", "retinaface-resnet50", "parsing-parsenet")
_lock = threading.Lock()
_inst: Optional["FaceRestorer"] = None


def available() -> bool:
    return all(model_path(k).is_file() for k in FACE_MODELS)


class FaceRestorer:
    def __init__(self) -> None:
        for key in FACE_MODELS:  # todos verificados ANTES de que facexlib pueda intentar descargar nada
            p = model_path(key)
            if not p.is_file():
                raise AppError("Falta el modelo de rostros. Ejecuta scripts/descargar_modelos.sh.", 503, "model_missing")
            if sha256_of(p) != MODELS[key].sha256:
                raise AppError("Un modelo de rostros no coincide con su checksum; vuelve a descargarlo.", 503, "model_corrupt")
        from facexlib.utils.face_restoration_helper import FaceRestoreHelper  # import diferido (pesado)

        self._helper_cls = FaceRestoreHelper
        self.device = pick_device()
        net = GFPGANv1Clean(
            out_size=512, num_style_feat=512, channel_multiplier=2, decoder_load_path=None, fix_decoder=False,
            num_mlp=8, input_is_latent=True, different_w=True, narrow=1, sft_half=True,
        )
        state = torch.load(model_path("gfpgan-v1.4"), map_location="cpu", weights_only=True)
        net.load_state_dict(state["params_ema"] if "params_ema" in state else state["params"], strict=True)
        self.net = net.eval().to(self.device)

    @torch.inference_mode()
    def _restore_crop(self, bgr_crop: np.ndarray) -> np.ndarray:
        rgb = cv2.cvtColor(bgr_crop, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        t = torch.from_numpy(rgb).permute(2, 0, 1).unsqueeze(0).to(self.device)
        t = (t - 0.5) / 0.5
        out = self.net(t, return_rgb=False, weight=0.5)[0]
        out = ((out.clamp(-1, 1) + 1) / 2).squeeze(0).permute(1, 2, 0).cpu().numpy()
        return cv2.cvtColor((out * 255.0 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR)

    def restore(
        self,
        rgb: np.ndarray,
        strength: float,
        exclude: Sequence[tuple[float, float, float, float]] = (),
        progress: Optional[Callable[[float], None]] = None,
        cancelled: Optional[Callable[[], bool]] = None,
    ) -> tuple[np.ndarray, int]:
        """rgb float32 [0,1] → (rgb restaurado, nº de rostros mejorados)."""
        bgr = cv2.cvtColor((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR)
        helper = self._helper_cls(
            1, face_size=512, crop_ratio=(1, 1), det_model="retinaface_resnet50", save_ext="png",
            use_parse=False, device=self.device, model_rootpath=str(settings.models_dir),
        )
        helper.read_image(bgr)
        n = helper.get_face_landmarks_5(only_center_face=False, resize=640, eye_dist_threshold=5)
        if n == 0:
            return rgb, 0
        helper.align_warp_face()
        done = 0
        for i, crop in enumerate(helper.cropped_faces):
            if cancelled and cancelled():
                raise Cancelled()
            x1, y1, x2, y2 = helper.det_faces[i][:4]
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            # det_faces está en coordenadas de la imagen leída (la misma que `rgb`)
            if any(bx <= cx <= bx + bw and by <= cy <= by + bh for bx, by, bw, bh in exclude):
                helper.add_restored_face(crop)
            else:
                restored = self._restore_crop(crop)
                w = float(np.clip(strength, 0, 1))
                mixed = cv2.addWeighted(restored, w, crop, 1 - w, 0)
                helper.add_restored_face(mixed)
                done += 1
            if progress:
                progress((i + 1) / len(helper.cropped_faces))
        if done == 0:
            helper.clean_all()
            return rgb, 0
        helper.get_inverse_affine(None)
        out = helper.paste_faces_to_input_image(upsample_img=bgr)
        helper.clean_all()
        return cv2.cvtColor(out, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0, done


def get_face_restorer() -> FaceRestorer:
    global _inst
    with _lock:
        if _inst is None:
            _inst = FaceRestorer()
        return _inst
