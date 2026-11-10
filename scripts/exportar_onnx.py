"""Exporta realesr-general-x4v3 a ONNX (para la versión que corre en el navegador) y verifica que coincide con PyTorch.
Requiere: pip install onnx onnxruntime onnxscript   Uso: python scripts/exportar_onnx.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch

from backend.app.models.registry import model_path
from backend.app.models.srvgg import SRVGGNetCompact

OUT = Path(__file__).resolve().parents[1] / "frontend" / "public" / "models" / "realesr-general-x4v3.onnx"
OUT.parent.mkdir(parents=True, exist_ok=True)

net = SRVGGNetCompact(3, 3, num_feat=64, num_conv=32, upscale=4, act_type="prelu")
st = torch.load(model_path("realesr-general-x4v3"), map_location="cpu", weights_only=True)
net.load_state_dict(st["params"] if "params" in st else st, strict=True)
net.eval()
x = torch.rand(1, 3, 64, 64)
torch.onnx.export(net, x, str(OUT), input_names=["input"], output_names=["output"], opset_version=17, dynamo=False,
                  dynamic_axes={"input": {2: "h", 3: "w"}, "output": {2: "H", 3: "W"}})
import onnxruntime as ort

sess = ort.InferenceSession(str(OUT), providers=["CPUExecutionProvider"])
worst = 0.0
for shape in ((1, 3, 64, 64), (1, 3, 96, 80), (1, 3, 33, 47)):
    t = torch.rand(*shape)
    ref = net(t).detach().numpy()
    got = sess.run(None, {"input": t.numpy()})[0]
    worst = max(worst, float(np.abs(ref - got).max()))
print(f"ONNX escrito: {OUT} ({OUT.stat().st_size / 1e6:.1f} MB) | diferencia máxima vs PyTorch: {worst:.2e}")
assert worst < 1e-3, "el ONNX no coincide con PyTorch"
