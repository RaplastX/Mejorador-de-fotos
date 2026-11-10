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
