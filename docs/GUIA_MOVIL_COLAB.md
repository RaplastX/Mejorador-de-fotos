# Usar la app solo con el móvil (Google Colab)

No hace falta PC ni claves de API. Usas **tu propia cuenta de Google** para abrir Colab, que presta una GPU gratuita; la app corre ahí y la ves en el navegador del móvil.

## Abrir el cuaderno
Enlace (pégalo en el navegador del móvil, con la sesión de Google iniciada):

https://colab.research.google.com/github/RaplastX/Mejorador-de-fotos/blob/ccr-e0aaf393-m6ujgv/notebooks/luma_colab.ipynb

Si no abre, activa *Sitio para ordenador* en el navegador. Si el repositorio fuese privado, Colab pedirá conectar GitHub.

## Pasos
1. *Entorno de ejecución → Cambiar tipo de entorno → GPU*.
2. Ejecuta las 3 celdas en orden. La celda 3 imprime un **enlace de emparejamiento**: ábrelo en otra pestaña.
3. Android: menú de Chrome → *Instalar app* (el túnel da HTTPS, así que se puede instalar). iPhone: Safari → Compartir → *Añadir a pantalla de inicio*. Ojo: el enlace cambia en cada sesión de Colab, así que el icono instalado solo sirve mientras dure esa sesión.

## Qué esperar (honesto)
- **No está probado de extremo a extremo.** El túnel y Colab no se pudieron ejecutar desde el entorno de desarrollo; el servidor, el emparejamiento y los modelos sí están probados en Linux. El primer uso real puede revelar fallos; si ocurre, copia el mensaje de error de la celda.
- **No es «sin límite»:** Colab gratuito tiene cuota diaria de GPU variable, no garantiza disponibilidad y corta sesiones inactivas. Todo se borra al terminar la sesión.
- **Rendimiento en GPU: no medido.** Las cifras de `RENDIMIENTO.md` son de CPU.
- **Privacidad:** las fotos van a la máquina de Colab (cuenta de Google) y el tráfico pasa por Cloudflare (túnel *quick*, sin cuenta, para pruebas). Con el token, solo quien tenga tu enlace puede usar la app.
- Los *quick tunnels* de Cloudflare no tienen garantía de servicio.
