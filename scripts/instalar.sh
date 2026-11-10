#!/usr/bin/env bash
# Instalación reproducible. Uso: scripts/instalar.sh [cpu|cuda]   (por defecto: cpu)
set -euo pipefail
cd "$(dirname "$0")/.."
VARIANTE="${1:-cpu}"
command -v python3 >/dev/null || { echo "Falta Python 3.10+"; exit 1; }
python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
if [ "$VARIANTE" = "cuda" ]; then
  .venv/bin/pip install -q "torch==2.15.0"           # rueda estándar de PyPI (incluye CUDA)
else
  .venv/bin/pip install -q "torch==2.15.0" --index-url https://download.pytorch.org/whl/cpu
fi
.venv/bin/pip install -q -r backend/requirements.txt
scripts/descargar_modelos.sh
if command -v npm >/dev/null; then
  (cd frontend && npm ci --silent && npm run build --silent)
else
  echo "AVISO: no hay Node/npm; la interfaz no se compilará (necesitas Node 20+ una sola vez)."
fi
echo "Instalación completa. Inicia con: scripts/iniciar.sh"
