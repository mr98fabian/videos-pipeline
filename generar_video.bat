@echo off
REM Doble clic para generar un video automatico (elige el siguiente tema de topics.txt).
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File scripts\run_auto.ps1
pause
