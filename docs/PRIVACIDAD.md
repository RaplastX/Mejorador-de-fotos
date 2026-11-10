# Privacidad

- El servidor escucha solo en `127.0.0.1` y rechaza cabeceras `Host` ajenas.
- El backend no importa ninguna librería de red cliente (comprobado con `grep`) y el frontend no contiene URLs externas. En la prueba E2E con navegador, **0 peticiones** fueron a hosts distintos de localhost.
- Única conexión de red de la app: `scripts/descargar_modelos.sh` (acción explícita del usuario, GitHub oficial) y la instalación de dependencias.
- Sin telemetría, anuncios, cuentas ni reconocimiento de identidad. Los rostros se detectan como cajas para el diagnóstico y no se almacenan ni se calculan plantillas biométricas.
- Temporales en `~/.local/share/luma-enhance/sessions` (permisos 0700); se borran al cerrar el servidor, al borrar una foto, o con «Borrar historial y temporales» en Ajustes.
- Las exportaciones eliminan por defecto EXIF y GPS; conservar GPS exige activarlo expresamente.
- Limitación: no hay prueba automática de tráfico a nivel de sistema operativo (solo a nivel de navegador y revisión de código).

## Modo móvil (`LUMA_REMOTE=1` / `scripts/iniciar-movil.sh`)
- Escucha en la red local/VPN y **exige token** en todas las rutas (salvo manifest, service worker e iconos). Sin token: 401.
- Token de 256 bits en `~/.local/share/luma-enhance/token` (0600), comparado en tiempo constante; cookie HttpOnly, SameSite=Strict.
- Las fotos viajan solo entre tu móvil y tu PC. En Wi-Fi doméstica por HTTP no van cifradas en la red local; con Tailscale (`tailscale serve`) sí.
- El service worker cachea solo la carcasa de la app, nunca fotos ni respuestas de `/api`.
- Sin limitación de intentos contra fuerza bruta del token (inviable por su longitud, pero no hay bloqueo).
- No se usa ninguna cuenta de terceros ni API en la nube.

## Modo túnel / Colab (`python -m backend.launch_tunnel`)
- Rompe la regla de «las fotos no salen de tu equipo»: viajan a la máquina de Colab (cuenta de Google del usuario) y el tráfico HTTPS atraviesa la red de Cloudflare, que termina el cifrado en su borde y técnicamente podría verlo. Úsalo solo si lo aceptas.
- El servidor escucha solo en 127.0.0.1; únicamente el túnel llega a él, y todo exige el token (256 bits).
- Las fotos y temporales viven en el disco de la sesión de Colab y se pierden al cerrarla.
- `cloudflared` se descarga de github.com/cloudflare/cloudflared sin verificar checksum (no automatizado).

## Sitio público (Cloudflare Worker + KV)
- Sirve solo ficheros estáticos (app, modelo, runtime). **Las fotos nunca se envían**: el procesado ocurre en el dispositivo (verificado: solo hay peticiones al propio dominio y a Google Fonts).
- Cloudflare ve lo habitual de un sitio web (IP, cabeceras, ficheros pedidos); Google Fonts ve la IP al cargar las tipografías. La app no incluye analítica ni cookies.
- Las exportaciones salen sin EXIF/GPS.
