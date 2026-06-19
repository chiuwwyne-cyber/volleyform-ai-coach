$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ToolsDir = Join-Path $Root "tools"
$Cloudflared = Join-Path $ToolsDir "cloudflared.exe"
$DownloadUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"

if (-not (Test-Path $ToolsDir)) {
    New-Item -ItemType Directory -Path $ToolsDir | Out-Null
}

Write-Host "Downloading cloudflared to:" -ForegroundColor Green
Write-Host $Cloudflared -ForegroundColor Cyan
Write-Host "Source: $DownloadUrl" -ForegroundColor Cyan

Invoke-WebRequest -Uri $DownloadUrl -OutFile $Cloudflared -UseBasicParsing

if (-not (Test-Path $Cloudflared)) {
    Write-Host "Download failed." -ForegroundColor Red
    exit 1
}

Write-Host "cloudflared is ready." -ForegroundColor Green
Write-Host "Next command:" -ForegroundColor Yellow
Write-Host ".\run_remote_tunnel.ps1" -ForegroundColor Cyan
