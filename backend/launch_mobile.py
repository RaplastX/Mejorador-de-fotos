"""Inicia el motor en modo móvil: escucha en la red local/VPN y exige emparejamiento por token.

Uso: python -m backend.launch_mobile      (o scripts/iniciar-movil.sh)
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess

os.environ["LUMA_REMOTE"] = "1"

import qrcode  # noqa: E402
import uvicorn  # noqa: E402

from .app.core import auth  # noqa: E402
from .app.core.config import APP_NAME, settings  # noqa: E402


def lan_ips() -> list[str]:
    ips: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # no envía nada: solo elige la interfaz de salida
            ips.append(s.getsockname()[0])
    except OSError:
        pass
    if shutil.which("tailscale"):
        try:
            out = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=5).stdout.split()
            ips += [i for i in out if i not in ips]
        except Exception:
            pass
    return ips


def main() -> None:
    tok = auth.get_token()
    print(f"\n=== {APP_NAME} · modo móvil ===")
    print("Abre UNA de estas direcciones en el móvil (misma Wi-Fi o VPN Tailscale) para emparejarlo:\n")
    for ip in lan_ips() or ["<IP-de-tu-PC>"]:
        url = f"http://{ip}:{settings.port}/pair?t={tok}"
        print(" ", url)
    first = (lan_ips() or ["127.0.0.1"])[0]
    qr = qrcode.QRCode(border=1)
    qr.add_data(f"http://{first}:{settings.port}/pair?t={tok}")
    qr.print_ascii(invert=True)
    print("\nEl enlace contiene tu clave privada: no lo compartas. Para revocar el acceso borra:", settings.token_file)
    print("Cierra con Ctrl+C.\n")
    uvicorn.run("backend.app.main:app", host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
