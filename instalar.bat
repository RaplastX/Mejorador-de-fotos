@echo off
rem Instalador para Windows (SIN PROBAR en Windows real: se escribio y reviso en Linux). Doble clic para ejecutar.
chcp 65001 >nul
cd /d "%~dp0"
echo === Luma Enhance: instalacion ===
where py >nul 2>nul && (set PY=py -3) || (where python >nul 2>nul && (set PY=python) || (
  echo No se encontro Python. Instalalo desde https://www.python.org/downloads/ marcando "Add python.exe to PATH" y vuelve a ejecutar.
  pause & exit /b 1))
%PY% --version
if not exist .venv ( %PY% -m venv .venv || ( echo No se pudo crear el entorno. & pause & exit /b 1 ) )
call .venv\Scripts\python -m pip install --upgrade pip
nvidia-smi >nul 2>nul
if %errorlevel%==0 (
  echo Tarjeta NVIDIA detectada: se instala PyTorch con CUDA ^(unos 2,5 GB^).
  call .venv\Scripts\pip install torch==2.14.1 torchvision==0.29.1 --index-url https://download.pytorch.org/whl/cu126 || goto :error
) else (
  echo No se detecto NVIDIA: se instala PyTorch para CPU.
  call .venv\Scripts\pip install torch==2.15.0 torchvision==0.29.2 || goto :error
)
call .venv\Scripts\pip install -r backend\requirements.txt || goto :error
call .venv\Scripts\pip install --no-deps facexlib==0.3.0 || goto :error
echo Descargando modelos de IA ^(~1 GB, una sola vez^)...
call .venv\Scripts\python scripts\descargar_modelos.py || goto :error
echo.
echo Instalacion completa. Usa "iniciar.bat" ^(en este PC^) o "iniciar-movil.bat" ^(desde el telefono^).
pause
exit /b 0
:error
echo.
echo HUBO UN ERROR. Copia el mensaje de arriba y envialo para poder ayudarte.
pause
exit /b 1
