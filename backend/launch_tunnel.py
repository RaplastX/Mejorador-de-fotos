"""Inicia el motor y lo publica por un túnel HTTPS de Cloudflare (quick tunnel, sin cuenta) para usarlo desde el móvil
cuando no hay un PC propio, p. ej. dentro de Google Colab con GPU gratuita.

- El servidor escucha SOLO en 127.0.0.1; únicamente el túnel llega a él.
- Todo exige el token de emparejamiento (modo remoto). La URL del túnel es pública pero inútil sin el token.
- Los quick tunnels de Cloudflare son para pruebas: sin garantía de disponibilidad. La URL cambia en cada ejecución.
- ESTADO: la lógica de servidor y del enlace está probada; el túnel real NO se ha podido probar de extremo a extremo
  (el entorno de desarrollo bloquea abrir túneles hacia internet). Se probará por primera vez en Colab.

Uso: python -m backend.launch_tunnel
"""
from __future__ import annotations

import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import time
import urllib.request

os.environ["LUMA_REMOTE"] = "1"
os.environ["LUMA_BIND"] = "127.0.0.1"

from .app.core import auth  # noqa: E402
from .app.core.config import APP_NAME, REPO_ROOT, settings  # noqa: E402

CF_FILE = {"x86_64": "cloudflared-linux-amd64", "amd64": "cloudflared-linux-amd64", "aarch64": "cloudflared-linux-arm64", "arm64": "cloudflared-linux-arm64"}
TUNNEL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def find_tunnel_url(text: str) -> str | None:
    m = TUNNEL_RE.search(text)
    return m.group(0) if m else None


def pairing_link(url: str, token: str) -> str:
    return f"{url.rstrip('/')}/pair?t={token}"


def get_cloudflared() -> str:
    found = shutil.which("cloudflared")
    if found:
        return found
    name = CF_FILE.get(platform.machine().lower())
    if platform.system() != "Linux" or not name:
        sys.exit("Este lanzador solo descarga cloudflared para Linux. Instálalo a mano desde developers.cloudflare.com y reintenta.")
    dest = REPO_ROOT / "bin" / "cloudflared"
    if not dest.is_file():
        dest.parent.mkdir(exist_ok=True)
        print("Descargando cloudflared (~40 MB) desde github.com/cloudflare/cloudflared …", flush=True)
        urllib.request.urlretrieve(f"https://github.com/cloudflare/cloudflared/releases/latest/download/{name}", dest)
        dest.chmod(dest.stat().st_mode | stat.S_IEXEC)
    return str(dest)


def wait_http(url: str, tries: int = 90) -> bool:
    for _ in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False


def main() -> None:
    port = settings.port
    tok = auth.get_token()
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=REPO_ROOT,
    )
    tunnel = None
    try:
        if not wait_http(f"http://127.0.0.1:{port}/manifest.webmanifest"):
            sys.exit("El servidor no arrancó. Revisa los mensajes de arriba.")
        tunnel = subprocess.Popen([get_cloudflared(), "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"], stderr=subprocess.PIPE, text=True)
        url = None
        t0 = time.time()
        for line in tunnel.stderr:  # type: ignore[union-attr]
            url = find_tunnel_url(line)
            if url or time.time() - t0 > 90:
                break
        if not url:
            sys.exit("No se pudo abrir el túnel (Cloudflare no respondió).")
        link = pairing_link(url, tok)
        print(f"\n=== {APP_NAME} listo ===\nAbre este enlace EN EL MÓVIL (contiene tu clave privada, no lo compartas):\n\n{link}\n", flush=True)
        try:
            import qrcode

            q = qrcode.QRCode(border=1)
            q.add_data(link)
            q.print_ascii(invert=True)
        except Exception:
            pass
        print("Deja esta celda en marcha mientras uses la app. Para cerrar, deténla.", flush=True)
        for _ in tunnel.stderr:  # mantiene vivo el túnel
            pass
    except KeyboardInterrupt:
        pass
    finally:
        for p in (tunnel, server):
            if p and p.poll() is None:
                p.terminate()


if __name__ == "__main__":
    main()
