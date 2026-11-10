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
| Restauración facial | **GFPGAN** (TencentARC) | Apache-2.0 (verificado) | No verificado | Candidato Fase 2 (depende de facexlib/basicsr) |
| Restauración facial | CodeFormer (sczhou) | **S-Lab 1.0, no comercial** (verificado) | No verificado | Aceptable solo para uso estrictamente personal; descartado por defecto |
| Inpainting | LaMa (advimman) | Apache-2.0 (verificado) | No verificado | Candidato Fase 3 |
| App de referencia | Upscayl | **AGPL-3.0** (verificado) | — | Solo inspiración; no se copia código |
| Detección facial | MediaPipe | Apache-2.0 (verificado) | — | Descartado: dependencia pesada para solo contar rostros |
| Detección facial | **Haar de OpenCV** | Apache-2.0 (OpenCV) | Incluidos en el paquete | **Elegido**: sin descargas, offline. YuNet (opencv_zoo) no pudo descargarse en este entorno (403) |
| Denoise/color/nitidez | OpenCV (NLM, CLAHE, LAB) | Apache-2.0 | — | **Elegido**: clásico, determinista, sin pesos |
| Runtime | PyTorch (CPU/CUDA) | BSD-style | — | **Elegido** (ONNX Runtime descartado: habría que convertir y mantener el modelo) |

## Costes reales
Todo el uso normal es gratuito: software y modelo sin coste. Sin GPU, el coste es tiempo de CPU (ver `RENDIMIENTO.md`). Sin servicios cloud.

## Hallazgo técnico
OpenCV 5.0 eliminó `CascadeClassifier`; se fija OpenCV 4.11.0.86.

## Pendiente de verificar antes de integrar
Licencia de los pesos de GFPGAN/LaMa/SwinIR/HAT y su disponibilidad en fuentes oficiales.
