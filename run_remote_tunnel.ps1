$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Server = Join-Path $Root "backend\server.py"
$BundledCloudflared = Join-Path $Root "tools\cloudflared.exe"
$CloudflaredCommand = $null

if (Test-Path $BundledCloudflared) {
    $CloudflaredCommand = $BundledCloudflared
}
else {
    $Cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($Cloudflared) {
        $CloudflaredCommand = $Cloudflared.Source
    }
}

if (-not (Test-Path $Python)) {
    Write-Host "Cannot find .venv Python. Please install requirements first." -ForegroundColor Red
    exit 1
}

if (-not $CloudflaredCommand) {
    Write-Host "Cannot find cloudflared." -ForegroundColor Red
    Write-Host "Run this project-local installer, then try again:" -ForegroundColor Yellow
    Write-Host ".\install_cloudflared.ps1" -ForegroundColor Cyan
    Write-Host "Manual download page:" -ForegroundColor Yellow
    Write-Host "https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/" -ForegroundColor Cyan
    exit 1
}

Write-Host "Starting local backend on http://127.0.0.1:8000 ..." -ForegroundColor Green
$Backend = Start-Process -FilePath $Python `
    -ArgumentList @($Server, "--host", "127.0.0.1", "--port", "8000") `
    -WorkingDirectory $Root `
    -WindowStyle Hidden `
    -PassThru

try {
    Start-Sleep -Seconds 2
    Write-Host "Starting public HTTPS tunnel..." -ForegroundColor Green
    Write-Host "Open the https://*.trycloudflare.com URL printed below on your phone." -ForegroundColor Cyan
    Write-Host "When opening the app through that public URL, keep Backend URL empty." -ForegroundColor Cyan

    $MaxAttempts = 3
    for ($Attempt = 1; $Attempt -le $MaxAttempts; $Attempt++) {
        if ($Attempt -gt 1) {
            Write-Host "Retrying tunnel connection ($Attempt / $MaxAttempts)..." -ForegroundColor Yellow
            Start-Sleep -Seconds 4
        }

        & $CloudflaredCommand tunnel --url "http://127.0.0.1:8000" --no-autoupdate
        $ExitCode = $LASTEXITCODE
        if ($ExitCode -eq 0) {
            break
        }
    }

    if ($ExitCode -ne 0) {
        Write-Host "Could not create the public tunnel." -ForegroundColor Red
        Write-Host "Please check your internet connection, firewall, or try again later." -ForegroundColor Yellow
        exit $ExitCode
    }
}
finally {
    if ($Backend -and -not $Backend.HasExited) {
        Stop-Process -Id $Backend.Id -Force
    }
}
