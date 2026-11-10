#!/usr/bin/env bash
# Descarga los pesos oficiales y verifica su SHA-256. Solo se contacta con github.com (releases oficiales de Real-ESRGAN, GFPGAN y facexlib).
# Uso: scripts/descargar_modelos.sh [--sin-rostros]   (rostros = ~540 MB; sin ellos solo hay superresolución)
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p models
bajar() { # archivo url sha
  local f="models/$1"
  if [ -f "$f" ] && echo "$3  $f" | sha256sum -c --quiet - 2>/dev/null; then echo "OK (ya presente): $1"; return; fi
  echo "Descargando $1 desde $2"
  curl -fL --retry 3 -o "$f" "$2"
  echo "$3  $f" | sha256sum -c - || { rm -f "$f"; echo "Checksum incorrecto: $1 eliminado."; exit 1; }
}
bajar realesr-general-x4v3.pth https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth 8dc7edb9ac80ccdc30c3a5dca6616509367f05fbc184ad95b731f05bece96292
if [ "${1:-}" != "--sin-rostros" ]; then
  bajar GFPGANv1.4.pth https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth e2cd4703ab14f4d01fd1383a8a8b266f9a5833dacee8e6a79d3bf21a1b6be5ad
  bajar detection_Resnet50_Final.pth https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth 6d1de9c2944f2ccddca5f5e010ea5ae64a39845a86311af6fdf30841b0a5a16d
  bajar parsing_parsenet.pth https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth 3d558d8d0e42c20224f13cf5a29c79eba2d59913419f945545d8cf7b72920de2
fi
