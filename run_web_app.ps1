$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Host "Cannot find .venv Python. Please install requirements first." -ForegroundColor Red
    exit 1
}

Write-Host "Starting Volleyball AI Coach backend..." -ForegroundColor Green
Write-Host "Local:  http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "Phone:  use this computer's LAN IP, for example http://192.168.x.x:8000" -ForegroundColor Cyan
Write-Host "Remote: run .\run_remote_tunnel.ps1 if the phone is not on the same network." -ForegroundColor Cyan

& $Python (Join-Path $Root "backend\server.py") --host 0.0.0.0 --port 8000
