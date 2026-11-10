# Privacidad

- El servidor escucha solo en `127.0.0.1` y rechaza cabeceras `Host` ajenas.
- El backend no importa ninguna librería de red cliente (comprobado con `grep`) y el frontend no contiene URLs externas. En la prueba E2E con navegador, **0 peticiones** fueron a hosts distintos de localhost.
- Única conexión de red de la app: `scripts/descargar_modelos.sh` (acción explícita del usuario, GitHub oficial) y la instalación de dependencias.
- Sin telemetría, anuncios, cuentas ni reconocimiento de identidad. Los rostros se detectan como cajas para el diagnóstico y no se almacenan ni se calculan plantillas biométricas.
- Temporales en `~/.local/share/luma-enhance/sessions` (permisos 0700); se borran al cerrar el servidor, al borrar una foto, o con «Borrar historial y temporales» en Ajustes.
- Las exportaciones eliminan por defecto EXIF y GPS; conservar GPS exige activarlo expresamente.
- Limitación: no hay prueba automática de tráfico a nivel de sistema operativo (solo a nivel de navegador y revisión de código).
