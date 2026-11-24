@echo off
REM Render unico del episodio 2 de la serie Pelando cable (creado por Kimi, 10 ago 2026).
REM Se lanza via Programador de tareas (schtasks) porque el render completo
REM (TTS + Flow + ffmpeg) supera el limite de ejecucion interactiva del agente.
REM %~dp0 = carpeta del .bat (scripts\); ".." = la raiz del repo, sea cual sea el checkout
cd /d "%~dp0.."
echo === Inicio: %DATE% %TIME% === > "logs\run_ep2_kimi.log"
py pipeline.py --script-file scripts/korex-tarjeta-minimo.json --flow --voice qw_korex >> "logs\run_ep2_kimi.log" 2>&1
echo === Fin: %DATE% %TIME% (exit %ERRORLEVEL%) === >> "logs\run_ep2_kimi.log"
