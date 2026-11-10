"""Publica la app en un Hugging Face Space (SDK Docker, CPU gratuita). Usa SOLO tu token de HF (variable HF_TOKEN).

  HF_TOKEN=... python scripts/publicar_space.py [--space usuario/nombre]

- Crea el Space PRIVADO (o público con --publico) si no existe, fija el secreto LUMA_TOKEN (clave de emparejamiento) si se genera una nueva, y sube el código.
- Imprime una sola vez el enlace de emparejamiento. Es tu clave privada: no lo compartas.
- Las fotos que se procesen en el Space pasan por los servidores de Hugging Face (ver docs/PRIVACIDAD.md)."""
import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://huggingface.co/api"
FRONT = """---
title: Luma Enhance
colorFrom: yellow
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
short_description: Mejora fotográfica privada con IA
---

Aplicación de mejora de fotos (superresolución, rostros, foto antigua, borrar objetos). Se abre con un enlace de
emparejamiento privado. Código: https://github.com/RaplastX/Mejorador-de-fotos
"""


def call(method: str, path: str, token: str, body: dict | None = None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw[:200].decode(errors="replace")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--space", help="usuario/nombre (por defecto: tu usuario/luma-enhance)")
    ap.add_argument("--publico", action="store_true", help="Space PÚBLICO (visible en internet; la app sigue exigiendo su clave). Por defecto es PRIVADO.")
    ap.add_argument("--token-emparejamiento", help="clave fija existente (>=32 caracteres); si no, se genera una nueva")
    a = ap.parse_args()
    tok = os.environ.get("HF_TOKEN")
    if not tok:
        sys.exit("Falta la variable HF_TOKEN.")
    st, me = call("GET", "/whoami-v2", tok)
    if st != 200:
        sys.exit(f"Token de Hugging Face no válido ({st}).")
    space = a.space or f"{me['name']}/luma-enhance"
    owner, name = space.split("/")

    st, r = call("POST", "/repos/create", tok, {"type": "space", "name": name, "organization": None if owner == me["name"] else owner, "sdk": "docker", "private": not a.publico})
    print("Crear Space", "PÚBLICO" if a.publico else "PRIVADO", ":", st, "(409 = ya existía)" if st == 409 else "")
    if st not in (200, 409):
        sys.exit(f"No se pudo crear el Space: {r}")

    pairing = a.token_emparejamiento or secrets.token_urlsafe(32)
    st, r = call("POST", f"/spaces/{space}/secrets", tok, {"key": "LUMA_TOKEN", "value": pairing, "description": "Clave de emparejamiento de la app"})
    print("Secreto LUMA_TOKEN:", st)
    if st != 200:
        sys.exit(f"No se pudo fijar el secreto: {r}")

    with tempfile.TemporaryDirectory() as tmp:
        dst = Path(tmp) / "space"
        files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split("\n")
        for f in filter(None, files):
            if f.startswith(("notebooks/", "docs/", "scripts/galeria")) or f.endswith((".bat",)):
                continue
            s = ROOT / f
            if s.is_file():
                (dst / f).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(s, dst / f)
        (dst / "README.md").write_text(FRONT, encoding="utf-8")
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        git = ["git", "-c", f"http.extraHeader=Authorization: Bearer {tok}", "-c", "user.name=luma", "-c", "user.email=luma@example.invalid"]
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=dst, check=True)
        subprocess.run(["git", "add", "-A"], cwd=dst, check=True)
        subprocess.run(["git", "-c", "user.name=luma", "-c", "user.email=luma@example.invalid", "commit", "-q", "-m", "Publicar Luma Enhance"], cwd=dst, check=True)
        r = subprocess.run(git + ["push", "-q", "--force", f"https://huggingface.co/spaces/{space}", "main"], cwd=dst, env=env, capture_output=True, text=True)
        if r.returncode:
            sys.exit("Falló el push: " + r.stderr.replace(tok, "***")[-400:])
    host = f"{owner}-{name}".lower().replace("_", "-").replace(".", "-")
    print(f"\nSpace subido. Se está construyendo (la primera vez tarda ~10 minutos): https://huggingface.co/spaces/{space}")
    print("Estado de la construcción: pestaña Logs del Space.")
    if not a.publico:
        print("El Space es PRIVADO: para abrirlo en el móvil debes tener la sesión de Hugging Face iniciada en ese navegador.")
    print(f"\nEnlace de emparejamiento (PRIVADO, ábrelo en el móvil):\nhttps://{host}.hf.space/pair?t={pairing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
