# Imagen para Hugging Face Spaces (SDK Docker, CPU gratuita). También sirve en cualquier host con Docker.
FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 LUMA_REMOTE=1 LUMA_PORT=7860 LUMA_DATA_DIR=/tmp/luma
RUN useradd -m -u 1000 user
USER user
WORKDIR /home/user/app
ENV PATH="/home/user/.local/bin:$PATH"

# 1) dependencias (capa estable)
COPY --chown=user backend/requirements.txt backend/requirements.txt
RUN pip install torch==2.15.0 torchvision==0.29.2 --index-url https://download.pytorch.org/whl/cpu \
 && pip install -r backend/requirements.txt \
 && pip install --no-deps facexlib==0.3.0

# 2) modelos oficiales con verificación SHA-256 (capa estable, ~1 GB)
COPY --chown=user backend/app/__init__.py backend/app/__init__.py
COPY --chown=user backend/app/core backend/app/core
COPY --chown=user backend/app/models/__init__.py backend/app/models/registry.py backend/app/models/
COPY --chown=user scripts/descargar_modelos.py scripts/descargar_modelos.py
RUN python scripts/descargar_modelos.py

# 3) la app (capa que cambia)
COPY --chown=user backend backend
COPY --chown=user frontend/dist frontend/dist

EXPOSE 7860
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers", "--forwarded-allow-ips=*"]
