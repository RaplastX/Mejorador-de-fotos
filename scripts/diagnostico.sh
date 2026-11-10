#!/usr/bin/env bash
# Muestra el estado del entorno para resolver problemas. No envía nada fuera del equipo.
cd "$(dirname "$0")/.."
echo "== Sistema =="; uname -sr; python3 --version; command -v node >/dev/null && node --version
echo "== Hardware =="; nproc | sed 's/^/CPU hilos: /'; free -h 2>/dev/null | sed -n 2p; (nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo "GPU NVIDIA: no detectada (se usará CPU)")
echo "== Python/paquetes =="; .venv/bin/python - <<'PY'
import importlib
for m in ("torch","cv2","numpy","PIL","fastapi","skimage"):
    try: print(m, importlib.import_module(m).__version__)
    except Exception as e: print(m, "NO DISPONIBLE:", e)
try:
    import torch; print("CUDA disponible:", torch.cuda.is_available())
except Exception: pass
PY
echo "== Modelo =="; sha256sum models/realesr-general-x4v3.pth 2>/dev/null || echo "Falta el modelo: ejecuta scripts/descargar_modelos.sh"
echo "== Interfaz =="; [ -f frontend/dist/index.html ] && echo "compilada" || echo "NO compilada (cd frontend && npm ci && npm run build)"
echo "== Puerto ${LUMA_PORT:-8765} =="; (curl -s -m 3 "http://127.0.0.1:${LUMA_PORT:-8765}/api/system" >/dev/null && echo "servidor activo") || echo "servidor detenido"
