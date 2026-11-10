# Pruebas ejecutadas (2026-11-10, v0.3.0)

| Prueba | Resultado |
|---|---|
| `pytest` (37 tests: lo anterior + rayones, geometría, sombras, colorización, borrado, ojos rojos, TIFF/HEIC, endpoints nuevos) | ✅ 37 passed |
| Rayones: atenúa los simulados y una foto sana casi no cambia (diff medio < 0,0015) | ✅ |
| Colorización: añade color y conserva la luminancia | ✅ |
| Borrado: 0 píxeles cambian lejos de la máscara | ✅ |
| E2E navegador: preset «Antigua en color», guardar preset, recortar 16:9 (600×400→600×338), rotar (→338×600), «Imagen anterior» dos veces, pintar con pincel y borrar | ✅ sin errores de consola ni peticiones externas |
| Imagen real del usuario (512×512, muy desenfocada) | ⚠ mejora pequeña con ambos modelos; documentado como limitación |
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

**No probado**: «Guardar todas», HEIC real de iPhone, ojos rojos en fotos reales, rayones reales o diagonales, herramientas nuevas en pantalla de móvil, GPU, móvil físico, HTTPS con Tailscale, fotos reales de personas (solo imágenes libres de scikit-image), varios rostros reales (se simuló con la imagen duplicada), foto antigua real, texto/líneas finas, HEIC/TIFF, lotes de >1 archivo en navegador, ejecución desde cero con `instalar.sh` en otra máquina, métricas PSNR/SSIM/LPIPS (poco informativas con resultados generativos).

## Rediseño (v0.3.1)
| Prueba | Resultado |
|---|---|
| Capturas iPhone 13 emulado y 1360 px: portada, editor, barra de acción fija | ✅ revisadas visualmente |
| E2E recortar 16:9, rotar, imagen anterior ×2, pincel y borrar tras el rediseño | ✅ sin errores de consola |
| Publicación en Hugging Face Space | ❌ no posible gratis (402 PRO); no se creó nada |
| Túnel Cloudflare / Colab | ⚠ sin probar (entorno de desarrollo lo bloquea) |
| Imagen Docker | ⚠ nunca construida (sin demonio Docker) |

## Motor en el navegador (v0.4.0)
| Prueba | Resultado |
|---|---|
| ONNX vs PyTorch (3 tamaños dinámicos) | ✅ diferencia máxima 1e-6 |
| Servidor estático sin API → la app detecta y usa el motor del navegador | ✅ |
| Subir foto, diagnóstico, 2×, exportar JPEG 512×512 sin EXIF | ✅ 7,5–7,9 s (WASM 1 hilo, CPU de servidor) |
| Resultado del navegador vs servidor (misma foto, mismos ajustes) | ✅ diferencia media 0,019; visualmente igual |
| Variante del artefacto (solo WASM, servida desde una subcarpeta) | ✅ igual resultado |
| Publicación como Artifact privado de Claude | ⚠ publicado, **sin verificar dentro del visor de Claude** (WASM, workers y el nombre `.onnx.wasm` del modelo dependen de la sandbox) |
| WebGPU, hilos WASM, móvil físico, Safari | ❌ no probado |
| Cloudflare Pages | ❌ no publicado (sin autorización); un intento fallido de `wrangler` modificó el repo y se revirtió; no creó nada en la cuenta (verificado en lectura) |
