"""Sustituto mínimo de basicsr (Apache-2.0, XPixelGroup/BasicSR) para poder usar la arquitectura de GFPGAN
sin instalar basicsr (que no compila en Python recientes). Solo se necesita para inferencia."""
import torch
from torch import nn
from torch.nn import init
from torch.nn.modules.batchnorm import _BatchNorm


class _Registry:
    def register(self):
        return lambda cls: cls


ARCH_REGISTRY = _Registry()


@torch.no_grad()
def default_init_weights(module_list, scale=1, bias_fill=0, **kwargs):
    if not isinstance(module_list, list):
        module_list = [module_list]
    for module in module_list:
        for m in module.modules():
            if isinstance(m, (nn.Conv2d, nn.Linear)):
                init.kaiming_normal_(m.weight, **kwargs)
                m.weight.data *= scale
                if m.bias is not None:
                    m.bias.data.fill_(bias_fill)
            elif isinstance(m, _BatchNorm):
                init.constant_(m.weight, 1)
                if m.bias is not None:
                    m.bias.data.fill_(bias_fill)
