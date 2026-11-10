from __future__ import annotations

import io
from typing import Literal, Optional

from fastapi import APIRouter, File, Response, UploadFile
from fastapi.responses import FileResponse
from PIL import Image
from pydantic import BaseModel, Field

from ..core.config import APP_NAME, APP_VERSION, settings
from ..core.errors import AppError
from ..models import registry
from ..models.upscaler import hardware_info
from ..pipelines import enhance
from ..services import analysis, face_restore, faces, image_io
from ..services.store import get_store

router = APIRouter(prefix="/api")


class FaceBox(BaseModel):
    x: float
    y: float
    w: float
    h: float


class JobRequest(BaseModel):
    image_id: str
    intensity: Literal["suave", "equilibrada", "intensa"] = "equilibrada"
    denoise: Optional[float] = Field(None, ge=0, le=1)
    color: Optional[float] = Field(None, ge=0, le=1)
    sharpen: Optional[float] = Field(None, ge=0, le=1)
    upscale: bool = True
    target: Literal["original", "1080p", "2k", "4k"] = "original"
    scale: float = Field(2.0, ge=1, le=4)
    faces: bool = False
    face_strength: float = Field(0.7, ge=0, le=1)
    skin: bool = False
    skin_smooth: float = Field(0.35, ge=0, le=1)
    skin_wrinkles: float = Field(0.35, ge=0, le=1)
    keep_texture: bool = True
    exclude_faces: list[FaceBox] = Field(default_factory=list, max_length=64)

    def to_options(self) -> enhance.Options:
        return enhance.Options(
            intensity=self.intensity, denoise=self.denoise, color=self.color, sharpen=self.sharpen,
            upscale=self.upscale, target=self.target, scale=self.scale,
            faces=self.faces, face_strength=self.face_strength, skin=self.skin,
            skin_smooth=self.skin_smooth, skin_wrinkles=self.skin_wrinkles, keep_texture=self.keep_texture,
            exclude_faces=tuple((b.x, b.y, b.w, b.h) for b in self.exclude_faces),
        )


class ExportRequest(BaseModel):
    format: Literal["jpeg", "png", "webp"] = "jpeg"
    quality: int = Field(92, ge=40, le=100)
    keep_metadata: bool = False
    keep_gps: bool = False


def _job_json(job) -> dict:
    return {
        "id": job.id, "image_id": job.image_id, "status": job.status, "progress": round(job.progress, 3),
        "stage": job.stage, "error": job.error, "plan": job.plan, "seconds": job.seconds,
        "result": {"width": job.result_w, "height": job.result_h} if job.status == "done" else None,
    }


def _jpeg(data: bytes) -> Response:
    return Response(data, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"})


@router.get("/system")
def system():
    return {
        "app": APP_NAME, "version": APP_VERSION, "hardware": hardware_info(),
        "limits": {"max_upload_mb": settings.max_upload_bytes // (1024 * 1024), "max_input_mp": settings.max_input_pixels // 1_000_000,
                   "max_output_mp": settings.max_output_pixels // 1_000_000, "tile": settings.tile_size},
        "models": [registry.model_status(k) for k in registry.MODELS],
        "privacy": {"local_only": True, "telemetry": False, "host": settings.host},
        "features": {"upscale": registry.model_path("realesr-general-x4v3").is_file(), "face_detection": True,
                     "face_restoration": face_restore.available(), "skin_retouch": True, "inpainting": False},
    }


@router.post("/images")
async def upload(file: UploadFile = File(...)):
    data = await file.read(settings.max_upload_bytes + 1)
    rec, rgb = get_store().add_image(data, file.filename)
    return _image_json(rec, rgb)


def _image_json(rec, rgb) -> dict:
    boxes = faces.detect_faces(rgb)
    info = analysis.analyze(rgb, len(boxes))
    return {
        "id": rec.id, "name": rec.name, "format": rec.fmt, "width": rec.width, "height": rec.height, "size": rec.size,
        "has_alpha": rec.has_alpha, "analysis": info, "faces": [{"x": x, "y": y, "w": w, "h": h} for x, y, w, h in boxes],
    }


@router.get("/images")
def list_images():
    recs = sorted(get_store().images.values(), key=lambda r: r.created, reverse=True)
    return [{"id": r.id, "name": r.name, "width": r.width, "height": r.height, "size": r.size} for r in recs[:24]]


@router.get("/images/{image_id}")
def image_info(image_id: str):
    store = get_store()
    rec = store.get_image(image_id)
    return _image_json(rec, store.load_working(rec))


@router.get("/images/{image_id}/display")
def image_display(image_id: str):
    rec = get_store().get_image(image_id)
    return _jpeg((rec.dir / "display.jpg").read_bytes())


@router.delete("/images/{image_id}", status_code=204)
def image_delete(image_id: str):
    get_store().delete_image(image_id)
    return Response(status_code=204)


@router.post("/plan")
def plan(req: JobRequest):
    rec = get_store().get_image(req.image_id)
    return enhance.plan_output(rec.width, rec.height, req.to_options())


@router.post("/jobs", status_code=202)
def create_job(req: JobRequest):
    if req.faces and not face_restore.available():
        raise AppError("Faltan los modelos de rostros. Ejecuta scripts/descargar_modelos.sh.", 503, "model_missing")
    if req.upscale and not registry.model_path("realesr-general-x4v3").is_file():
        raise AppError("Falta el modelo de superresolución. Ejecuta scripts/descargar_modelos.sh.", 503, "model_missing")
    job = get_store().create_job(req.image_id, req.to_options(), req.model_dump())
    return _job_json(job)


@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    return _job_json(get_store().get_job(job_id))


@router.delete("/jobs/{job_id}")
def job_cancel(job_id: str):
    job = get_store().get_job(job_id)
    job.cancel.set()
    return _job_json(job)


@router.get("/jobs/{job_id}/display")
def job_display(job_id: str):
    store = get_store()
    job = store.get_job(job_id)
    if job.status != "done":
        raise AppError("El resultado aún no está listo.", 409, "not_ready")
    return _jpeg((store.job_dir(job) / "display.jpg").read_bytes())


@router.post("/jobs/{job_id}/export")
def job_export(job_id: str, req: ExportRequest):
    store = get_store()
    job = store.get_job(job_id)
    if job.status != "done":
        raise AppError("El resultado aún no está listo.", 409, "not_ready")
    rec = store.get_image(job.image_id)
    pil = Image.open(store.job_dir(job) / "result.png")
    pil.load()
    src_exif = Image.open(store.original_path(rec)).getexif() if req.keep_metadata else None
    alpha = None
    apath = rec.dir / "alpha.npy"
    if rec.has_alpha and apath.is_file():
        import numpy as np

        alpha = np.load(apath)
    data = image_io.export_image(pil, req.format, req.quality, req.keep_metadata, req.keep_gps, src_exif, alpha)
    ext = image_io.EXPORT_FORMATS[req.format][1]
    name = image_io.unique_name(rec.name, ext, set())
    mime = {"jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}[req.format]
    return Response(data, media_type=mime, headers={
        "Content-Disposition": f'attachment; filename="{name}"', "X-Output-Width": str(pil.width), "X-Output-Height": str(pil.height),
        "X-Output-Bytes": str(len(data)), "X-Content-Type-Options": "nosniff"})


@router.delete("/data", status_code=204)
def clear_data():
    get_store().clear_all()
    return Response(status_code=204)
