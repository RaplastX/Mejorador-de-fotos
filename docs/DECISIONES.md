# Decisiones de arquitectura

- **Web local servida por FastAPI** (React + TS + Vite + Tailwind), no Electron/Tauri aún: menos runtimes, instalación simple, y Tauri se evalúa en la Fase 5 cuando el motor esté estable.
- **Un solo worker de trabajos** (`ThreadPoolExecutor(1)`): la inferencia ya usa todos los hilos de CPU; paralelizar solo aumentaría la memoria. Cancelación cooperativa entre mosaicos.
- **Sondeo HTTP (polling) en vez de WebSocket**: progreso real sin complejidad adicional.
- **Orden del pipeline**: denoise (más ligero si habrá SR, pues el modelo ya suaviza) → exposición/color → superresolución ×4 → remuestreo único a la talla final (AREA si reduce, CUBIC si amplía) → nitidez reducida a la mitad tras SR. Se evita reescalar dos veces.
- **Factor <4 con modelo ×4**: se ejecuta ×4 y se reduce una vez (comportamiento equivalente a `outscale` de Real-ESRGAN).
- **Mosaicos de 192 px con 16 px de solape**: acotan la memoria; un test verifica diferencia <0,02 frente a pasada completa.
- **Original inmutable**: se guarda con permisos 0400; todo se procesa desde él.
- **Seguridad**: bind 127.0.0.1, `TrustedHostMiddleware` (anti DNS-rebinding), IDs UUID validados por regex (sin rutas del usuario), nombres de salida saneados, validación por contenido, límites de bytes/píxeles de entrada y salida, errores sin trazas ni rutas.
- **Funciones no implementadas** (cara/piel/inpainting) se anuncian como no disponibles (`features` en `/api/system` = false) en vez de simularse.
- **Descartado**: ONNX Runtime, MediaPipe, Electron, cuentas/BD, nube.

## v0.2.0
- **Móvil = PWA + PC como motor**: un teléfono no ejecuta estos modelos con calidad razonable, y no hay API en la nube gratuita sin límites. Alternativa descartada: app nativa con modelo ligero (mucho menos calidad).
- **Autenticación solo en modo remoto**, por token + cookie; en modo local se mantiene `TrustedHost` sin credenciales.
- **GFPGAN sin basicsr**: se vendoriza la arquitectura clean con shim. Mezcla ajustable restaurado/original para preservar identidad (en lugar del parámetro interno `weight`).
- **Retoque de piel clásico, no generativo**: separación de frecuencias en máscara de piel; así no cambia identidad y es reversible (no destructivo, siempre desde el original). Detector Haar para sus cajas (limitación conocida).
- **Preajustes de color más suaves** tras ver que «equilibrada» sobreactuaba contraste en la galería.
