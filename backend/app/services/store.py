"""Almacén de sesión en disco privado (modo 0700): originales intactos, resultados y trabajos."""
from __future__ import annotations

import os
import re
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from ..core.config import settings
from ..core.errors import AppError, Cancelled
from ..pipelines import enhance
from . import image_io

_ID = re.compile(r"^[0-9a-f]{32}$")


def check_id(value: str) -> str:
    if not _ID.match(value or ""):
        raise AppError("Identificador no válido.", 400, "bad_id")
    return value


@dataclass
class ImageRec:
    id: str
    name: str
    fmt: str
    width: int
    height: int
    size: int
    dir: Path
    has_alpha: bool = False
    created: float = field(default_factory=time.time)


@dataclass
class Job:
    id: str
    image_id: str
    options: dict
    plan: dict
    status: str = "queued"  # queued | running | done | cancelled | error
    progress: float = 0.0
    stage: str = "En cola"
    error: Optional[str] = None
    result_w: int = 0
    result_h: int = 0
    seconds: float = 0.0
    created: float = field(default_factory=time.time)
    cancel: threading.Event = field(default_factory=threading.Event)


class Store:
    def __init__(self) -> None:
        self.images: dict[str, ImageRec] = {}
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="luma-worker")
        self.root = settings.sessions_dir
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)

    # ---------- imágenes ----------
    def add_image(self, data: bytes, filename: str | None) -> tuple[ImageRec, np.ndarray]:
        img = image_io.validate_and_open(data)
        fmt = img.format or "PNG"
        iid = uuid.uuid4().hex
        d = self.root / iid
        d.mkdir(mode=0o700)
        try:
            (d / f"original.{image_io.ALLOWED_FORMATS[fmt]}").write_bytes(data)  # original intacto, solo lectura
            os.chmod(d / f"original.{image_io.ALLOWED_FORMATS[fmt]}", 0o400)
            rgb, alpha = image_io.to_working_array(img)
            if alpha is not None:
                np.save(d / "alpha.npy", alpha)
            rec = ImageRec(iid, image_io.safe_stem(filename), fmt, rgb.shape[1], rgb.shape[0], len(data), d, alpha is not None)
            (d / "display.jpg").write_bytes(image_io.make_display_jpeg(image_io.array_to_pil(rgb)))
        except Exception:
            shutil.rmtree(d, ignore_errors=True)
            raise
        with self.lock:
            self.images[iid] = rec
        return rec, rgb

    def get_image(self, iid: str) -> ImageRec:
        rec = self.images.get(check_id(iid))
        if not rec:
            raise AppError("La imagen no existe o ya se eliminó.", 404, "not_found")
        return rec

    def original_path(self, rec: ImageRec) -> Path:
        return rec.dir / f"original.{image_io.ALLOWED_FORMATS[rec.fmt]}"

    def load_working(self, rec: ImageRec) -> np.ndarray:
        img = Image.open(self.original_path(rec))
        rgb, _ = image_io.to_working_array(img)
        return rgb

    # ---------- trabajos ----------
    def create_job(self, image_id: str, opts: enhance.Options, raw: dict) -> Job:
        rec = self.get_image(image_id)
        plan = enhance.plan_output(rec.width, rec.height, opts)
        job = Job(uuid.uuid4().hex, rec.id, raw, plan)
        with self.lock:
            self.jobs[job.id] = job
        self.pool.submit(self._run_job, job, rec, opts)
        return job

    def get_job(self, jid: str) -> Job:
        job = self.jobs.get(check_id(jid))
        if not job:
            raise AppError("El trabajo no existe.", 404, "not_found")
        return job

    def _run_job(self, job: Job, rec: ImageRec, opts: enhance.Options) -> None:
        if job.cancel.is_set():
            job.status, job.stage = "cancelled", "Cancelado"
            return
        job.status = "running"
        t0 = time.time()

        def progress(p: float, stage: str) -> None:
            job.progress, job.stage = p, stage

        try:
            rgb = self.load_working(rec)
            out = enhance.run(rgb, opts, progress, job.cancel.is_set)
            pil = image_io.array_to_pil(out)
            jdir = rec.dir / "jobs" / job.id
            jdir.mkdir(parents=True, exist_ok=True)
            pil.save(jdir / "result.png", compress_level=1)
            (jdir / "display.jpg").write_bytes(image_io.make_display_jpeg(pil))
            job.result_w, job.result_h = pil.size
            job.seconds = round(time.time() - t0, 2)
            job.status, job.stage, job.progress = "done", "Listo", 1.0
        except Cancelled:
            job.status, job.stage = "cancelled", "Cancelado"
        except AppError as e:
            job.status, job.error, job.stage = "error", e.message, "Error"
        except MemoryError:
            job.status, job.error, job.stage = "error", "Memoria insuficiente. Prueba un objetivo menor o un tamaño de mosaico más pequeño.", "Error"
        except Exception:  # sin filtrar rutas ni trazas al usuario
            import logging

            logging.getLogger("luma").exception("fallo procesando trabajo %s", job.id)
            job.status, job.error, job.stage = "error", "Ocurrió un error inesperado al procesar la imagen.", "Error"

    def job_dir(self, job: Job) -> Path:
        return self.get_image(job.image_id).dir / "jobs" / job.id

    # ---------- limpieza ----------
    def delete_image(self, iid: str) -> None:
        rec = self.get_image(iid)
        for j in [j for j in self.jobs.values() if j.image_id == iid]:
            j.cancel.set()
            self.jobs.pop(j.id, None)
        with self.lock:
            self.images.pop(rec.id, None)
        shutil.rmtree(rec.dir, ignore_errors=True)

    def clear_all(self) -> None:
        for j in self.jobs.values():
            j.cancel.set()
        self.jobs.clear()
        self.images.clear()
        shutil.rmtree(self.root, ignore_errors=True)
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)


_store: Optional[Store] = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store()
    return _store
