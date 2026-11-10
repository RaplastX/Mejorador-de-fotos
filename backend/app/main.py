from __future__ import annotations

import logging
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .api.routes import router
from .core.config import APP_NAME, APP_VERSION, settings
from .core.errors import AppError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.sessions_dir.mkdir(parents=True, exist_ok=True)
    yield
    if settings.delete_temp_on_exit:
        shutil.rmtree(settings.sessions_dir, ignore_errors=True)


def create_app() -> FastAPI:
    app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    # Protege contra DNS-rebinding: solo se atiende a localhost.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])

    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse({"error": exc.code, "message": exc.message}, status_code=exc.status)

    app.include_router(router)

    dist = settings.frontend_dist
    if dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        async def spa(path: str):
            if path == "api" or path.startswith("api/"):
                return JSONResponse({"error": "not_found", "message": "Ruta no encontrada."}, status_code=404)
            f = (dist / path).resolve()
            if path and f.is_file() and dist.resolve() in f.parents:
                return FileResponse(f)
            return FileResponse(dist / "index.html")

    return app


app = create_app()
