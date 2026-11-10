"""Configuración central. El nombre de la aplicación vive solo aquí."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

APP_NAME = "Luma Enhance"  # nombre provisional: cambiar solo aquí y en frontend/src/brand.ts
APP_VERSION = "0.2.0"

REPO_ROOT = Path(__file__).resolve().parents[3]


def _default_data_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "luma-enhance"


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(os.environ.get("LUMA_DATA_DIR", _default_data_dir())))
    models_dir: Path = field(default_factory=lambda: Path(os.environ.get("LUMA_MODELS_DIR", REPO_ROOT / "models")))
    frontend_dist: Path = field(default_factory=lambda: REPO_ROOT / "frontend" / "dist")
    # Por defecto solo local. LUMA_REMOTE=1 abre el servidor a la red local/VPN y EXIGE token de emparejamiento.
    remote: bool = os.environ.get("LUMA_REMOTE", "0") == "1"
    host: str = field(default_factory=lambda: "0.0.0.0" if os.environ.get("LUMA_REMOTE", "0") == "1" else "127.0.0.1")
    port: int = int(os.environ.get("LUMA_PORT", "8765"))
    max_upload_bytes: int = 60 * 1024 * 1024
    max_input_pixels: int = 60_000_000  # 60 MP
    max_output_pixels: int = int(os.environ.get("LUMA_MAX_OUTPUT_PIXELS", 40_000_000))
    tile_size: int = int(os.environ.get("LUMA_TILE", "192"))
    tile_overlap: int = 16
    delete_temp_on_exit: bool = True
    torch_threads: int = int(os.environ.get("LUMA_THREADS", "0"))  # 0 = automático
    device_preference: str = os.environ.get("LUMA_DEVICE", "auto")  # auto | cpu | cuda

    @property
    def token_file(self) -> Path:
        return self.data_dir / "token"

    @property
    def sessions_dir(self) -> Path:
        return self.data_dir / "sessions"


settings = Settings()
