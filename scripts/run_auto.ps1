# Ejecuta un video automatico y guarda un log por corrida.
# Pensado para ser llamado por el Programador de tareas de Windows.
# Uso manual: powershell -ExecutionPolicy Bypass -File scripts\run_auto.ps1

$ErrorActionPreference = "Continue"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$logDir = Join-Path $projectRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir ("run_{0}.log" -f (Get-Date -Format "yyyy-MM-dd_HHmmss"))

"=== Inicio: $(Get-Date -Format o) ===" | Out-File -FilePath $logFile -Encoding utf8

py pipeline.py --auto 2>&1 | Tee-Object -FilePath $logFile -Append

"=== Fin: $(Get-Date -Format o) (exit $LASTEXITCODE) ===" | Out-File -FilePath $logFile -Append -Encoding utf8

# Conserva solo los ultimos 30 logs para no acumular basura indefinidamente
Get-ChildItem $logDir -Filter "run_*.log" | Sort-Object LastWriteTime -Descending |
    Select-Object -Skip 30 | Remove-Item -Force -ErrorAction SilentlyContinue

exit $LASTEXITCODE
