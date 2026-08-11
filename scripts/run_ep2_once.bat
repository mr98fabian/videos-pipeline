@echo off
REM Render unico del episodio 2 de la serie Pelando cable (creado por Kimi, 10 ago 2026).
REM Se lanza via Programador de tareas (schtasks) porque el render completo
REM (TTS + Flow + ffmpeg) supera el limite de ejecucion interactiva del agente.
cd /d "C:\Users\Khine\Desktop\Workspace\Proyectos_Software\Videos"
echo === Inicio: %DATE% %TIME% === > "logs\run_ep2_kimi.log"
py pipeline.py --script-file scripts/korex-tarjeta-minimo.json --flow --voice qw_korex >> "logs\run_ep2_kimi.log" 2>&1
echo === Fin: %DATE% %TIME% (exit %ERRORLEVEL%) === >> "logs\run_ep2_kimi.log"
