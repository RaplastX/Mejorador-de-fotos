# Luma Enhance (nombre provisional)

Aplicación **local y privada** de mejora fotográfica con IA para uso personal y familiar. Las fotos no salen de tu equipo: sin cuentas, sin telemetría, sin servicios de pago.

> Nombre centralizado en `backend/app/core/config.py` (`APP_NAME`) y `frontend/src/brand.ts`.

## Estado real de las funciones (v0.3.0)

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
| Restauración facial con IA (GFPGAN v1.4): intensidad, y activar/desactivar cada rostro | ✅ Completa (probada) |
| Retoque natural de piel y arrugas (edición clásica, conserva textura, intensidades independientes) | ✅ Completa (probada en un rostro frontal) |
| Uso desde el móvil (Android/iPhone) como app instalable (PWA), con el PC como motor y emparejamiento por token | ✅ Probada en iPhone emulado; **no probada en un móvil físico** |
| Foto antigua: quitar rayones finos y polvo (clásico) | ✅ Probada con rayones simulados verticales; no detecta diagonales ni daños grandes |
| Colorización con IA (DDColor) | ✅ Probada; los colores son inventados (plausibles, no reales) |
| Borrar objetos con pincel (LaMa) | ✅ Probada; solo cambia la zona marcada |
| Recortar (proporciones), rotar 90° y enderezar; «Imagen anterior» para volver | ✅ Probada en navegador |
| Sombras/luces, ojos rojos, modelo de calidad alta (RealESRGAN_x4plus) | ✅ Sombras/luces y calidad alta probadas; ojos rojos solo con pupilas pintadas, no con fotos reales |
| Presets (5 incluidos + los tuyos, guardados en el navegador), versiones y «Guardar todas» | ✅ Presets probados en navegador; «Guardar todas» sin probar |
| Entrada TIFF y HEIC (iPhone) | ✅ Probada con archivos generados; no con un HEIC real de iPhone |
| Corrección de perspectiva, colorización por zonas, selección con lazo | ⏳ No implementado |
| Empaquetado como instalador (Tauri) | ⏳ Fase 5 |

## Sitio público
**https://luma-enhance.dylandavenxglob.workers.dev** (Cloudflare Worker + KV, plan gratuito). Es la versión del navegador: fotos 100 % en el dispositivo, sin límites de uso por parte de la app. Publicado con `python scripts/publicar_worker.py --site <carpeta compilada> --confirmo-publico`; el Worker está en `cloudflare/worker.js` (sirve ficheros gzip desde KV con las cabeceras de aislamiento que activan los hilos WASM; `no-transform` evita que el borde de Cloudflare los recomprima).

## Versión que corre en el navegador (sin servidor)
La misma interfaz funciona **sin servidor**: si no encuentra la API, usa un motor propio en el navegador (ONNX Runtime Web, con WebGPU si el dispositivo lo permite y WASM si no). Las fotos no salen del dispositivo.
- Incluye: superresolución 2×/4×/1080p/2K/4K, ruido, color, sombras/luces, nitidez, recorte, giro y enderezado, lotes, presets y versiones.
- **No incluye** (modelos de cientos de MB): rostros, piel, rayones, colorización, borrar objetos, ojos rojos, EXIF, HEIC/TIFF. Se desactivan con aviso.
- Calidad: resultado casi idéntico al del servidor (diferencia media 0,019 en una prueba). Rendimiento medido: 256→512 px en 7,5–7,9 s con WASM de un hilo en CPU de servidor; **WebGPU y móvil real no medidos**. Fotos de más de 1 MP tardan mucho sin GPU; el límite es 4 MP de entrada para ampliar y 12 MP de salida.
- Compilar: `cd frontend && npm ci && npm run build` (sitio estático en `frontend/dist`; copia el runtime de ONNX desde `node_modules`). Para el artefacto de Claude: `npm run build:artifact` (variante solo-WASM, 17 MB).
- Regenerar el modelo: `python scripts/exportar_onnx.py` (verifica contra PyTorch).
- **Por qué Worker+KV y no Pages**: en este entorno el proxy sustituye la cabecera `Authorization` de `api.cloudflare.com`, y la subida de ficheros de Pages usa un token temporal propio (error 8000013). Existe un proyecto Pages vacío `luma-enhance` creado en ese intento; se puede borrar desde el panel. No uses wrangler 4.153 (`pages project create` se delega en Workers y modifica el repo).
- Sin service worker en el sitio público: **no funciona sin conexión**.

## Alojar en internet (para usar sin PC)
- **Hugging Face Spaces: ya no es gratis para esto.** Probado 2026-11-10: crear un Space Docker en `cpu-basic` devuelve «requires a PRO subscription» (HTTP 402). Por eso no hay Space publicado. `Dockerfile` y `scripts/publicar_space.py` (privado por defecto, `--publico` explícito) quedan listos por si se paga PRO o se usa otro host con Docker. La imagen nunca se construyó: no hay demonio Docker en el entorno de desarrollo.
- Cualquier host con Docker: `docker build -t luma .` y `docker run -p 7860:7860 -e LUMA_TOKEN=<clave de 32+ caracteres> luma`; el enlace de emparejamiento es `https://<host>/pair?t=<clave>`.

## Solo con el móvil (sin PC): Google Colab
Ver **`docs/GUIA_MOVIL_COLAB.md`** y `notebooks/luma_colab.ipynb` (GPU gratuita con tu cuenta de Google; **sin probar de extremo a extremo**, con cuotas de Google).

## Windows
Ver **`docs/GUIA_WINDOWS.md`** (`instalar.bat`, `iniciar.bat`, `iniciar-movil.bat`; sin probar en Windows real).

## Instalación (Linux/macOS)

Requisitos: Python 3.10+ y Node 20+ (Node solo para compilar la interfaz una vez).

```bash
scripts/instalar.sh        # CPU (por defecto). Con GPU NVIDIA: scripts/instalar.sh cuda
scripts/iniciar.sh         # abre http://127.0.0.1:8765
```

Tras instalar, **funciona sin conexión**. Diagnóstico: `scripts/diagnostico.sh`.

### Modelos
`scripts/descargar_modelos.sh` descarga desde releases oficiales de GitHub, verificando SHA-256: todos los modelos (~1,0 GB: superresolución rápida y alta, rostros, borrar objetos, colorización). Con `--minimo` solo baja la superresolución rápida (5 MB) y el resto de funciones aparecen como no instaladas. DDColor se descarga de huggingface.co. Nada se descarga por su cuenta al usar la app. Para actualizarlo, cambia URL y checksum en `backend/app/models/registry.py` y en el script. Los pesos no se incluyen en el repositorio.

### Variables opcionales
`LUMA_PORT`, `LUMA_DEVICE=cpu|cuda|auto`, `LUMA_TILE` (tamaño de mosaico, baja si falta memoria), `LUMA_MAX_OUTPUT_PIXELS`, `LUMA_THREADS`, `LUMA_DATA_DIR`.

## Sobre Google Flow / Gemini
La app **no** usa cuentas de Google: Flow no tiene API y no se pedirá nunca correo ni contraseña.

## Uso desde el móvil (el PC hace el trabajo, sin límites ni cuotas)
No existe ninguna API en la nube gratuita y sin límites para esto, y las suscripciones (p. ej. Google AI Pro/Flow) no dan acceso a API. La opción gratuita e ilimitada es tu propio PC (con GPU NVIDIA si la hay):

```bash
scripts/iniciar-movil.sh     # muestra un enlace y un QR de emparejamiento
```
1. Móvil y PC en la **misma Wi-Fi**: abre el enlace/QR en el móvil una vez. Queda emparejado (cookie privada de 1 año).
2. **Fuera de casa**: instala [Tailscale](https://tailscale.com) (gratis) en PC y móvil y usa la IP de Tailscale que imprime el script. No se abre ningún puerto a internet.
3. **Instalar como app**: Android (Chrome) → menú → "Instalar app". iPhone (Safari) → Compartir → "Añadir a pantalla de inicio". La instalación completa de PWA exige HTTPS: con Tailscale ejecuta `tailscale serve --bg 8765` y usa la URL https que da. Por HTTP simple en Wi-Fi funciona como página web/atajo.
4. Para revocar el acceso, borra `~/.local/share/luma-enhance/token` y reinicia.

Seguridad: sin el token todo devuelve 401; el token (256 bits) se guarda con permisos 0600; el enlace de emparejamiento contiene la clave, no lo compartas. No hay cifrado en HTTP por Wi-Fi doméstica: usa Tailscale o `tailscale serve` si la red no es de confianza.

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
Galería de resultados reales: ver la página publicada (también reproducible con `scripts/galeria_datos.py`).
`docs/INVESTIGACION_TECNICA.md` · `docs/DECISIONES.md` · `docs/PRIVACIDAD.md` · `docs/RENDIMIENTO.md` · `docs/PRUEBAS.md`

## Limitaciones conocidas
- Sin GPU, 4K es lento (ver `docs/RENDIMIENTO.md`).
- La superresolución **reconstruye** detalle plausible; no recupera información inexistente. Con fuentes muy comprimidas puede dibujar halos y texturas "pintadas" en rostros.
- La restauración facial reconstruye rasgos: con intensidad alta puede alterar ligeramente la expresión; usa 50–70 %. Solo actúa en rostros frontales detectados (el retoque de piel usa un detector Haar, menos robusto con perfiles o caras pequeñas).
- **Una foto muy desenfocada mejora poco**: el detalle que no existe no se recupera (comprobado con una imagen real muy borrosa, también con el modelo de calidad alta).
- El modelo de calidad alta es ~12× más lento en CPU y en las pruebas la diferencia frente al rápido fue pequeña.
- Recortar, girar y borrar objetos crean una imagen nueva guardada como PNG: los metadatos EXIF del original no se conservan en esas imágenes.
- La vista en pantalla se reduce a 2048 px; la exportación usa la resolución completa.
- Los trabajos y temporales viven solo mientras el servidor está activo (se borran al cerrarlo).
- Auditoría npm: 0 vulnerabilidades en dependencias de producción; hay avisos en herramientas de desarrollo (no van en la app compilada).
