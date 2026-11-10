# Pruebas ejecutadas (2026-11-10, v0.2.0)

| Prueba | Resultado |
|---|---|
| `pytest` (27 tests: API, formatos, seguridad, mosaicos, rostros, piel, autenticación móvil) | ✅ 27 passed |
| Rostros: GFPGAN cambia el rostro, la exclusión por rostro lo protege (cambio 0,0038 → 0,0004) | ✅ |
| Piel: no toca nada fuera del rostro, conserva el tono medio, «conservar textura» retiene más detalle | ✅ |
| Modo móvil: 401 sin token, token falso 401, emparejamiento fija cookie HttpOnly/Strict, token 0600 | ✅ |
| E2E en iPhone 13 emulado (Playwright): emparejar → subir → mejorar → comparador sin desbordes | ✅ (móvil físico: **no probado**) |
| Galería de 6 casos con pipeline real y métricas frente a la referencia | ✅ (ver página publicada) |
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

**Visto en las pruebas**: la superresolución sola deforma ojos y boca en fuentes muy degradadas y la restauración facial lo corrige; en texto la IA inventa trazos; PSNR/SSIM de Luma son menores que los de bicúbica en ampliaciones (más nitidez inventada), mayores en el caso de poca luz.

**No probado**: GPU, móvil físico, HTTPS con Tailscale, fotos reales de personas (solo imágenes libres de scikit-image), varios rostros reales (se simuló con la imagen duplicada), foto antigua real, texto/líneas finas, HEIC/TIFF, lotes de >1 archivo en navegador, ejecución desde cero con `instalar.sh` en otra máquina, métricas PSNR/SSIM/LPIPS (poco informativas con resultados generativos).
