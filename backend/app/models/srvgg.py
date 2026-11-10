"""Arquitectura SRVGGNetCompact (Real-ESRGAN, BSD-3-Clause, Xintao Wang).

Reimplementación mínima y compatible con los pesos oficiales ``realesr-general-x4v3.pth``
para no depender de basicsr. Estructura idéntica: las claves del state_dict coinciden.
"""
from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F


class SRVGGNetCompact(nn.Module):
    def __init__(self, num_in_ch=3, num_out_ch=3, num_feat=64, num_conv=16, upscale=4, act_type="prelu"):
        super().__init__()
        self.upscale = upscale
        self.body = nn.ModuleList()
        self.body.append(nn.Conv2d(num_in_ch, num_feat, 3, 1, 1))
        self.body.append(self._act(act_type, num_feat))
        for _ in range(num_conv):
            self.body.append(nn.Conv2d(num_feat, num_feat, 3, 1, 1))
            self.body.append(self._act(act_type, num_feat))
        self.body.append(nn.Conv2d(num_feat, num_out_ch * upscale * upscale, 3, 1, 1))
        self.upsampler = nn.PixelShuffle(upscale)

    @staticmethod
    def _act(kind: str, num_feat: int) -> nn.Module:
        if kind == "relu":
            return nn.ReLU(inplace=True)
        if kind == "prelu":
            return nn.PReLU(num_parameters=num_feat)
        return nn.LeakyReLU(negative_slope=0.1, inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = x
        for layer in self.body:
            out = layer(out)
        out = self.upsampler(out)
        return out + F.interpolate(x, scale_factor=self.upscale, mode="nearest")
