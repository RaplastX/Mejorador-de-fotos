# Pruebas ejecutadas (2026-11-10)

| Prueba | Resultado |
|---|---|
| `pytest` (19 tests: API, formatos, seguridad, mosaicos, utilidades) | ✅ 19 passed |
| Importar JPEG/PNG/WebP, procesar 2× y exportar los tres formatos con tamaño correcto | ✅ |
| Rechazo: archivo vacío, texto, GIF, ejecutable con extensión .jpg, demasiados píxeles | ✅ |
| Host ajeno rechazado; IDs con `../` rechazados; ruta `/api/*` inexistente → JSON 404; SPA no lee fuera de `dist` | ✅ (esta última detectó y corrigió un fallo real) |
| Original intacto (SHA-256 antes/después) | ✅ |
| Exportación sin EXIF por defecto; con EXIF sin GPS; con GPS solo si se pide | ✅ |
| Alfa conservado en PNG | ✅ |
| Objetivos 1080p/4K calculan tamaño y avisos; límite de salida aplicado | ✅ |
| Cancelar un trabajo | ✅ |
| Borrar una imagen elimina sus archivos | ✅ |
| Mosaicos sin costuras (diff máx <0,02 vs pasada completa) | ✅ |
| `tsc` + `eslint` + `vite build` | ✅ sin errores |
| E2E en Chromium (Playwright): importar → 4K → comparar → exportar → deshacer → ajustes | ✅ sin errores de consola, 0 peticiones externas, JPEG de 3840×3840 |
| Evaluación visual | Mejora clara de bloques JPEG y bordes. **Defectos observados**: halo claro alrededor del cabello y piel suavizada en una fuente degradada a propósito (JPEG q=35); el balance de blancos puede enfriar el tono de fondo. |

**No probado**: GPU, varios rostros, foto antigua, texto/líneas finas, HEIC/TIFF, lotes de >1 archivo en navegador, ejecución desde cero con `instalar.sh` en otra máquina, métricas PSNR/SSIM/LPIPS (poco informativas con resultados generativos).
