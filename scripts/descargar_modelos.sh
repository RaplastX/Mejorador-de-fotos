#!/usr/bin/env bash
# Descarga los pesos oficiales y verifica su SHA-256. Solo se contacta con github.com (releases oficiales de Real-ESRGAN).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p models
F=models/realesr-general-x4v3.pth
URL=https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth
SHA=8dc7edb9ac80ccdc30c3a5dca6616509367f05fbc184ad95b731f05bece96292
if [ -f "$F" ] && echo "$SHA  $F" | sha256sum -c --quiet - 2>/dev/null; then echo "Modelo ya presente y verificado."; exit 0; fi
echo "Descargando $URL (~5 MB, licencia BSD-3-Clause)…"
curl -fL --retry 3 -o "$F" "$URL"
echo "$SHA  $F" | sha256sum -c - || { rm -f "$F"; echo "Checksum incorrecto: archivo eliminado."; exit 1; }
