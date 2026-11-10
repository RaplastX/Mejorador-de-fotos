#!/usr/bin/env bash
# Inicia la app para usarla desde el móvil (el PC hace el trabajo). Muestra enlace y QR de emparejamiento.
set -euo pipefail
cd "$(dirname "$0")/.."
exec .venv/bin/python -m backend.launch_mobile
