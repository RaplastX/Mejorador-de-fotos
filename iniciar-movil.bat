@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe ( echo Primero ejecuta instalar.bat & pause & exit /b 1 )
echo Si Windows pregunta por el Firewall, permite el acceso en redes PRIVADAS.
.venv\Scripts\python -m backend.launch_mobile
pause
