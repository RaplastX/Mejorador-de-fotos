# Rendimiento (medido)

Equipo de medición: **VM en la nube, Intel Xeon 2,1 GHz, 4 vCPU, 15 GB RAM, sin GPU**, PyTorch 2.15.0 CPU, mosaico 192 px. Script: `scripts/benchmark.py ANCHO ALTO ESCALA` (un proceso por medición; imagen = retrato de prueba reescalado). Intensidad equilibrada (denoise + color + SR + nitidez).

| Entrada | Factor | Salida | Tiempo | RAM pico |
|---|---|---|---|---|
| 640×480 | 2× | 1280×960 | 4,1 s | 545 MB |
| 1280×720 | 2× | 2560×1440 | 11,3 s | 725 MB |
| 1280×720 | 3× | 3840×2160 (4K) | 11,1 s | 1108 MB |
| 1920×1080 | 2× | 3840×2160 (4K) | 19,7 s | 1073 MB |
| 2000×1500 | 1× (sin SR) | 2000×1500 | 2,1 s | 638 MB |

Notas: el coste depende del tamaño de **entrada** (el modelo corre siempre a ×4 y luego se reduce). **No medido**: GPU (no disponible aquí). La referencia RTX 3050 / Ryzen 5 5600X del prompt **no se ha probado**; cualquier cifra para ese equipo sería una estimación. VRAM: no aplicable en esta medición.

## Rostros y piel (misma CPU)
| Caso | Tiempo | Nota |
|---|---|---|
| 256×256 → 1024×1024, 4× + GFPGAN (1 rostro) + piel | 6,0 s | incluye carga de modelos (primera vez) |
| 256×256 → 1024×1024, solo 4× | 0,7 s | modelo ya cargado |
| Foto antigua 300×300 → 1200×1200, 4× + GFPGAN | 3,6 s | |
RAM/tiempo con fotos grandes y varios rostros: **no medido**. GFPGAN procesa cada rostro a 512 px, así que el coste crece con el nº de rostros.

## Funciones de v0.3.0 (misma CPU)
| Operación | Tiempo |
|---|---|
| Superresolución 512×512 → 2048×2048, modelo rápido | 3,4 s |
| Igual, modelo de calidad alta (RealESRGAN_x4plus) | 42,8 s |
| Colorizar 600×400 (incluye carga del modelo) | 2,5 s |
| Borrar un objeto en 600×400 (incluye carga del modelo) | 1,7–2,1 s |
| Foto antigua 300×300 → 1200×1200: rayones + colorizar + 4× + rostro | 6,3 s |
No medido: memoria pico de estas funciones, ni fotos grandes.
