# Guía para Windows (PC con tarjeta NVIDIA) + móvil

> **Aviso honesto:** los `.bat` se escribieron y revisaron en Linux; **no se han ejecutado en Windows real**. Si algo falla, copia el mensaje de error y se corrige. El PyTorch con CUDA para Windows es la 2.14.1 (no existe aún la 2.15 con CUDA para Windows).

## Instalar (una vez)
1. Instala **Python 3.13** desde python.org (marca *Add python.exe to PATH*). Con tarjeta NVIDIA, ten los drivers actualizados.
2. Descarga el proyecto (botón verde *Code → Download ZIP* en GitHub, rama `ccr-e0aaf393-m6ujgv`) y descomprímelo.
3. Doble clic en **`instalar.bat`**. Tarda (descarga ~2,5 GB de PyTorch con CUDA y ~1 GB de modelos). No hace falta instalar Node: la interfaz ya viene compilada.

## Usar en el PC
Doble clic en **`iniciar.bat`**: se abre el navegador en `http://127.0.0.1:8765`.

## Usar desde el móvil
1. Doble clic en **`iniciar-movil.bat`**. Si Windows pregunta por el Firewall, permite **redes privadas**.
2. Aparece un enlace y un QR. Con el móvil en la **misma Wi-Fi**, escanea el QR (o abre el enlace). Queda emparejado.
3. Android: menú de Chrome → *Instalar app*. iPhone: Safari → Compartir → *Añadir a pantalla de inicio*.
4. Fuera de casa: instala Tailscale (gratis) en PC y móvil y abre el enlace con la IP de Tailscale. La instalación completa como app exige HTTPS (`tailscale serve --bg 8765`).

El PC tiene que estar encendido. No se usa ninguna cuenta de Google ni servicio en la nube.
