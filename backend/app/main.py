from __future__ import annotations

import logging
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .api.routes import router
from .core import auth
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
    if settings.remote:
        # Modo móvil: cualquier Host de la red local/VPN, pero TODO exige el token (protege también frente a DNS-rebinding).
        auth.get_token()

        @app.middleware("http")
        async def require_token(request: Request, call_next):
            path = request.url.path
            if path == "/pair":
                if auth.token_ok(request.query_params.get("t")):
                    resp = RedirectResponse("/", status_code=303)
                    resp.set_cookie(auth.COOKIE, auth.get_token(), httponly=True, samesite="strict", max_age=60 * 60 * 24 * 365)
                    return resp
                return JSONResponse({"error": "unauthorized", "message": "Enlace de emparejamiento no válido."}, status_code=401)
            if auth.is_public(path) or auth.token_ok(request.cookies.get(auth.COOKIE)):
                return await call_next(request)
            if path.startswith("/api/"):
                return JSONResponse({"error": "unauthorized", "message": "Dispositivo no emparejado. Escanea el QR del PC."}, status_code=401)
            return JSONResponse({"error": "unauthorized", "message": "Dispositivo no emparejado. Escanea el QR que muestra el PC."}, status_code=401)
    else:
        # Solo local: protege contra DNS-rebinding.
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
