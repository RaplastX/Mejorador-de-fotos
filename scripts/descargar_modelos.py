"""Descarga los modelos oficiales y verifica su SHA-256 (multiplataforma). Usa el mismo registro que la app.
Uso: python scripts/descargar_modelos.py [--minimo]    (--minimo = solo superresolución rápida, 5 MB)"""
import hashlib
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.models.registry import MODELS  # noqa: E402
from backend.app.core.config import settings  # noqa: E402

MINIMO = ("realesr-general-x4v3",)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    keys = MINIMO if "--minimo" in sys.argv else tuple(MODELS)
    settings.models_dir.mkdir(parents=True, exist_ok=True)
    fallos = 0
    for k in keys:
        m = MODELS[k]
        dest = settings.models_dir / m.filename
        if dest.is_file() and sha256(dest) == m.sha256:
            print(f"OK (ya presente): {m.filename}")
            continue
        print(f"Descargando {m.filename} desde {m.url}", flush=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        try:
            with urllib.request.urlopen(m.url, timeout=60) as r, open(tmp, "wb") as f:
                total, done = int(r.headers.get("Content-Length", 0)), 0
                while chunk := r.read(1 << 20):
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        print(f"\r  {done * 100 // total}%", end="", flush=True)
            print()
            if sha256(tmp) != m.sha256:
                tmp.unlink(missing_ok=True)
                print(f"  ERROR: checksum incorrecto, archivo eliminado: {m.filename}")
                fallos += 1
                continue
            tmp.replace(dest)
        except Exception as e:  # red caída, host bloqueado, etc.
            tmp.unlink(missing_ok=True)
            print(f"  ERROR descargando {m.filename}: {e}")
            fallos += 1
    print("Listo." if not fallos else f"Terminó con {fallos} fallo(s): vuelve a ejecutar para reintentar.")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
