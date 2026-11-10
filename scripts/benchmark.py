"""Mide tiempo y memoria pico reales del pipeline en este equipo. Uso: python scripts/benchmark.py ANCHO ALTO ESCALA"""
import json, resource, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from skimage import data
import cv2
from backend.app.pipelines import enhance
from backend.app.models.upscaler import hardware_info

w, h, scale = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
src = cv2.resize(data.astronaut(), (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
t = time.time()
out = enhance.run(src, enhance.Options(target="original", scale=scale), lambda p, s: None, lambda: False)
print(json.dumps({"in": f"{w}x{h}", "scale": scale, "out": f"{out.shape[1]}x{out.shape[0]}", "seconds": round(time.time() - t, 1),
                  "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024, "device": hardware_info()["device"]}))
