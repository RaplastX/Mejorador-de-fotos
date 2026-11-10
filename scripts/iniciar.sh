#!/usr/bin/env bash
# Inicia la aplicación solo en 127.0.0.1 y abre el navegador (si hay uno disponible).
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${LUMA_PORT:-8765}"
[ -d frontend/dist ] || echo "AVISO: falta frontend/dist; compila con 'cd frontend && npm ci && npm run build'."
(sleep 2; (xdg-open "http://127.0.0.1:$PORT" || open "http://127.0.0.1:$PORT") >/dev/null 2>&1 || true) &
exec .venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port "$PORT"
