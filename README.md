# Luma Enhance (nombre provisional)

Aplicación **local y privada** de mejora fotográfica con IA para uso personal y familiar. Las fotos no salen de tu equipo: sin cuentas, sin telemetría, sin servicios de pago.

> Nombre centralizado en `backend/app/core/config.py` (`APP_NAME`) y `frontend/src/brand.ts`.

## Estado real de las funciones (v0.1.0 — Fase 1 / MVP)

| Función | Estado |
|---|---|
| Importar JPEG/PNG/WebP (validación por contenido real, EXIF respetado) | ✅ Completa |
| Diagnóstico (resolución, desenfoque, ruido, compresión, exposición, nº de rostros) | ✅ Completa |
| Reducción de ruido, exposición/color y nitidez anti-halo, con intensidad suave/equilibrada/intensa y sliders | ✅ Completa |
| Superresolución con IA (Real-ESRGAN compacto) 1×/2×/4× y objetivos 1080p/2K/4K, con mosaicos solapados | ✅ Completa |
| Comparador antes/después con divisor, zoom y desplazamiento; deshacer/rehacer | ✅ Completa |
| Exportar JPEG/PNG/WebP, calidad, EXIF opcional, **GPS eliminado por defecto**, alfa conservado en PNG/WebP | ✅ Completa |
| Procesamiento por lotes con progreso, cancelación segura y descarga individual | 🟡 Implementada, sin probar aún en navegador |
| Avisos de reconstrucción generativa y límites de memoria | ✅ Completa |
| Restauración facial con IA (GFPGAN), foto antigua, colorización | ⏳ Fase 2 — **no existe aún** (la UI lo indica) |
| Retoque natural de piel / arrugas | ⏳ Fase 3 — **no existe aún** |
| Eliminación de objetos (inpainting), recorte/enderezado, presets, HEIC/TIFF | ⏳ Pendiente |
| Empaquetado como instalador (Tauri) | ⏳ Fase 5 |

## Instalación (Linux/macOS; Windows: usa WSL o ejecuta los mismos pasos a mano)

Requisitos: Python 3.10+ y Node 20+ (Node solo para compilar la interfaz una vez).

```bash
scripts/instalar.sh        # CPU (por defecto). Con GPU NVIDIA: scripts/instalar.sh cuda
scripts/iniciar.sh         # abre http://127.0.0.1:8765
```

Tras instalar, **funciona sin conexión**. Diagnóstico: `scripts/diagnostico.sh`.

### Modelos
`scripts/descargar_modelos.sh` descarga **solo** el modelo oficial de Real-ESRGAN desde su release de GitHub y verifica el SHA-256. Para actualizarlo, cambia URL y checksum en `backend/app/models/registry.py` y en el script. Los pesos no se incluyen en el repositorio.

### Variables opcionales
`LUMA_PORT`, `LUMA_DEVICE=cpu|cuda|auto`, `LUMA_TILE` (tamaño de mosaico, baja si falta memoria), `LUMA_MAX_OUTPUT_PIXELS`, `LUMA_THREADS`, `LUMA_DATA_DIR`.

## Uso
1. **Mejorar fotografía** → elige una imagen (varias a la vez abre el modo por lotes).
2. Revisa el diagnóstico, elige intensidad y tamaño de salida. El tamaño final y los avisos se muestran **antes** de procesar.
3. **Mejorar imagen** → compara con el divisor → **Guardar copia**. El original nunca se modifica.

## Desarrollo
```bash
.venv/bin/pip install -r backend/requirements-dev.txt && .venv/bin/python -m pytest      # backend
cd frontend && npm run dev                                                              # UI con recarga (proxy a :8765)
cd frontend && npm run typecheck && npm run lint && npm run build
```

## Documentación
`docs/INVESTIGACION_TECNICA.md` · `docs/DECISIONES.md` · `docs/PRIVACIDAD.md` · `docs/RENDIMIENTO.md` · `docs/PRUEBAS.md`

## Limitaciones conocidas
- Sin GPU, 4K es lento (ver `docs/RENDIMIENTO.md`).
- La superresolución **reconstruye** detalle plausible; no recupera información inexistente. Con fuentes muy comprimidas puede dibujar halos y texturas "pintadas" en rostros.
- El modelo compacto prioriza velocidad; un modelo más grande (RealESRGAN_x4plus, SwinIR, HAT) daría más calidad pero no está integrado.
- La vista en pantalla se reduce a 2048 px; la exportación usa la resolución completa.
- Los trabajos y temporales viven solo mientras el servidor está activo (se borran al cerrarlo).
- Auditoría npm: 0 vulnerabilidades en dependencias de producción; hay avisos en herramientas de desarrollo (no van en la app compilada).
