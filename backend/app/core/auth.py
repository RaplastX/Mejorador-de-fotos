"""Emparejamiento por token para el modo remoto (móvil → PC). En modo local no hay autenticación.

El token (256 bits) se genera una vez, se guarda con permisos 0600 y se entrega al móvil
mediante un enlace/QR de un solo uso de emparejamiento que fija una cookie HttpOnly SameSite=Strict.
"""
from __future__ import annotations

import hmac
import os
import secrets

from .config import settings

COOKIE = "luma_token"
PUBLIC_PATHS = ("/pair", "/manifest.webmanifest", "/sw.js", "/icons/", "/favicon.ico")


def get_token() -> str:
    f = settings.token_file
    if f.is_file():
        return f.read_text().strip()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    tok = secrets.token_urlsafe(32)
    fd = os.open(f, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(tok)
    return tok


def token_ok(candidate: str | None) -> bool:
    return bool(candidate) and hmac.compare_digest(candidate.encode(), get_token().encode())


def is_public(path: str) -> bool:
    return any(path == p or path.startswith(p) for p in PUBLIC_PATHS)
