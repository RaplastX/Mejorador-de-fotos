# Investigación técnica

Fecha de consulta: **2026-11-10**. Licencias leídas del archivo `LICENSE` de la rama principal de cada repositorio oficial (GitHub raw). Si una fila dice «no verificado» no se ha comprobado.

## Correcciones al informe previo
El informe de partida contenía licencias erróneas. Verificado en los repositorios: **CodeFormer = S-Lab License 1.0, solo uso no comercial** (no Apache-2.0); **Upscayl = AGPL-3.0** (no MIT, y el repositorio es `upscayl/upscayl`); **GFPGAN = Apache-2.0** (no MIT). Además "Real-ESRGAN integra GFPGAN" es solo una opción (`--face_enhance`).

## Comparativa
| Tarea | Opción | Licencia código | Pesos | Veredicto |
|---|---|---|---|---|
| Superresolución | **Real-ESRGAN** `realesr-general-x4v3` (xinntao/Real-ESRGAN) | BSD-3-Clause (verificado) | Release oficial del mismo repo; sin licencia de pesos separada publicada | **Elegido**: 4,9 MB, viable en CPU, arquitectura simple (`SRVGGNetCompact`, reimplementada sin basicsr) |
| Superresolución | SwinIR (JingyunLiang/SwinIR) | Apache-2.0 (verificado) | No verificado | Alternativa: más lento en CPU; pendiente de evaluar |
| Superresolución | HAT (XPixelGroup/HAT) | Apache-2.0 (verificado) | No verificado | Alternativa de máxima calidad; exige GPU potente |
| Restauración facial | **GFPGAN v1.4** (TencentARC) | Apache-2.0 (verificado) | Release oficial del repo; sin licencia de pesos separada visible (dataset FFHQ: no verificado) | **Elegido e integrado**. `basicsr` no compila en Python 3.13, así que se vendoriza solo la arquitectura «clean» con un shim (`models/gfpgan_arch/`, aviso Apache-2.0 incluido) y se usa `facexlib` 0.3.0 (MIT) para detectar/alinear |
| Restauración facial | CodeFormer (sczhou) | **S-Lab 1.0, no comercial** (verificado) | No verificado | No integrado. No se comparó la calidad frente a GFPGAN (no la he medido); GFPGAN basta para uso familiar y tiene licencia permisiva |
| Inpainting | **LaMa big-lama** (advimman) | Apache-2.0 (verificado) | TorchScript reempaquetado por Sanster/IOPaint (Apache-2.0, verificado); licencia de pesos original no verificada por separado | **Integrado** (`torch.jit.load`, sin dependencias extra) |
| Colorización | **DDColor paper_tiny** (piddnad) | Apache-2.0 (verificado) | Apache-2.0 según la ficha oficial de Hugging Face | **Integrado**; arquitectura vendorizada en `models/ddcolor_arch/` |
| Superresolución alta | **RealESRGAN_x4plus** | BSD-3-Clause | Release oficial | **Integrado** como opción «Alta»; 42,8 s frente a 3,4 s en 512→2048 px (CPU) y mejora visual pequeña |
| HEIC | pillow-heif 1.8.1 | BSD-3 (no verificado en el repo; sus ruedas incluyen libheif, LGPL) | — | Integrado para leer fotos de iPhone |
| App de referencia | Upscayl | **AGPL-3.0** (verificado) | — | Solo inspiración; no se copia código |
| Detección facial | MediaPipe | Apache-2.0 (verificado) | — | Descartado: dependencia pesada para solo contar rostros |
| Detección facial | **Haar de OpenCV** | Apache-2.0 (OpenCV) | Incluidos en el paquete | **Elegido**: sin descargas, offline. YuNet (opencv_zoo) no pudo descargarse en este entorno (403) |
| Denoise/color/nitidez | OpenCV (NLM, CLAHE, LAB) | Apache-2.0 | — | **Elegido**: clásico, determinista, sin pesos |
| Runtime | PyTorch (CPU/CUDA) | BSD-style | — | **Elegido** (ONNX Runtime descartado: habría que convertir y mantener el modelo) |

## Costes reales
Todo el uso normal es gratuito: software y modelo sin coste. Sin GPU, el coste es tiempo de CPU (ver `RENDIMIENTO.md`). Sin servicios cloud.

## Hallazgo técnico
OpenCV 5.0 eliminó `CascadeClassifier`; se fija OpenCV 4.11.0.86.

## Pendiente de verificar
Licencia de los pesos de SwinIR/HAT y la original de LaMa, la licencia de pillow-heif, y los términos del dataset FFHQ con que se entrenó GFPGAN. Los SHA-256 de GFPGAN, RetinaFace, ParseNet, LaMa, DDColor y x4plus los fijé yo tras la primera descarga oficial; upstream no publica checksums.

## Incidencia corregida
`facexlib` descargaba por su cuenta `parsing_parsenet.pth` al crear el restaurador. Ahora es un modelo declarado, con checksum, que solo instala el script, y se verifica antes de que facexlib pueda intentar descargar nada.

## Nube y APIs gratuitas (consultado 2026-11-10)
- Google AI Pro/Flow: sus beneficios son de las apps web; el uso de la Gemini API se factura aparte ([docs de planes](https://ai.google.dev/gemini-api/docs/google-ai-plans)).
- Nivel gratuito de la Gemini API para modelos de imagen: ausente o muy limitado y cambiante según foros y terceros ([hilo](https://discuss.ai.google.dev/t/gemini-api-rate-limits-free-tier/125968)); no verificado en la tabla oficial.
- Pedir correo y contraseña de Google a una app es inseguro e incumple sus términos; no se implementa.
- Conclusión: el único camino gratuito sin cuotas es el PC propio.
