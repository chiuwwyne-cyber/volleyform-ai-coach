$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Server = Join-Path $Root "backend\server.py"
$BundledCloudflared = Join-Path $Root "tools\cloudflared.exe"
$RuntimeDir = Join-Path $Root "runtime"
$ShareConfig = Join-Path $Root "frontend\runtime-share.json"
$PublicFrontendUrl = "https://chiuwwyne-cyber.github.io/volleyform-ai-coach/"
$Port = 8000

if (-not (Test-Path $Python)) {
    Write-Host "Cannot find .venv Python. Please install requirements first." -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

function Get-LanUrl {
    param([int]$Port)
    $Sock = [System.Net.Sockets.Socket]::new(
        [System.Net.Sockets.AddressFamily]::InterNetwork,
        [System.Net.Sockets.SocketType]::Dgram,
        [System.Net.Sockets.ProtocolType]::Udp
    )
    try {
        $Sock.Connect("8.8.8.8", 80)
        $Address = $Sock.LocalEndPoint.Address.ToString()
        return "http://${Address}:$Port"
    }
    catch {
        return "http://127.0.0.1:$Port"
    }
    finally {
        $Sock.Close()
    }
}

function Get-CloudflaredCommand {
    if (Test-Path $BundledCloudflared) {
        return $BundledCloudflared
    }
    $Cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($Cloudflared) {
        return $Cloudflared.Source
    }
    return $null
}

function Wait-Backend {
    param([int]$Port)
    for ($i = 0; $i -lt 60; $i++) {
        try {
            $Response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 1 -UseBasicParsing
            if ($Response.StatusCode -eq 200) {
                return $true
            }
        }
        catch {}
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Start-BackendIfNeeded {
    param([int]$Port)
    try {
        $Response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 1 -UseBasicParsing
        if ($Response.StatusCode -eq 200) {
            Write-Host "Backend is already running." -ForegroundColor Green
            return $null
        }
    }
    catch {}

    $Stdout = Join-Path $RuntimeDir "backend_stdout.log"
    $Stderr = Join-Path $RuntimeDir "backend_stderr.log"
    Write-Host "Starting local backend API on port $Port..." -ForegroundColor Green
    $Process = Start-Process -FilePath $Python `
        -ArgumentList @($Server, "--host", "0.0.0.0", "--port", "$Port") `
        -WorkingDirectory $Root `
        -RedirectStandardOutput $Stdout `
        -RedirectStandardError $Stderr `
        -WindowStyle Hidden `
        -PassThru

    if (-not (Wait-Backend -Port $Port)) {
        Write-Host "Backend did not become ready. See runtime\backend_stderr.log." -ForegroundColor Red
        exit 1
    }
    return $Process
}

function Start-PublicBackendTunnel {
    param([int]$Port)
    $CloudflaredCommand = Get-CloudflaredCommand
    if (-not $CloudflaredCommand) {
        Write-Host "cloudflared not found. The public frontend will still open with on-device analysis." -ForegroundColor Yellow
        Write-Host "Run .\install_cloudflared.ps1 to enable public backend API tunneling." -ForegroundColor Yellow
        return ""
    }

    $Running = Get-Process cloudflared -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($Running) {
        Write-Host "A cloudflared process is already running. Reusing local/on-device mode for this launch." -ForegroundColor Yellow
        return ""
    }

    $Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $Stdout = Join-Path $RuntimeDir "cloudflared_stdout_$Stamp.log"
    $Stderr = Join-Path $RuntimeDir "cloudflared_stderr_$Stamp.log"

    Write-Host "Starting public HTTPS backend tunnel..." -ForegroundColor Green
    $Tunnel = Start-Process -FilePath $CloudflaredCommand `
        -ArgumentList @("tunnel", "--url", "http://127.0.0.1:$Port", "--no-autoupdate") `
        -WorkingDirectory $Root `
        -RedirectStandardOutput $Stdout `
        -RedirectStandardError $Stderr `
        -WindowStyle Hidden `
        -PassThru

    for ($i = 0; $i -lt 90; $i++) {
        $Text = ""
        if (Test-Path $Stdout) { $Text += Get-Content -LiteralPath $Stdout -Raw -ErrorAction SilentlyContinue }
        if (Test-Path $Stderr) { $Text += "`n" + (Get-Content -LiteralPath $Stderr -Raw -ErrorAction SilentlyContinue) }
        $Matches = [regex]::Matches($Text, "https://(?!api\.)[a-zA-Z0-9-]+\.trycloudflare\.com")
        if ($Matches.Count -gt 0) {
            $Url = $Matches[$Matches.Count - 1].Value
            Write-Host "Public backend API: $Url" -ForegroundColor Cyan
            return $Url
        }
        if ($Tunnel.HasExited) {
            break
        }
        Start-Sleep -Milliseconds 500
    }

    Write-Host "Could not get a public backend tunnel. The public frontend will still run on-device." -ForegroundColor Yellow
    Write-Host "See the latest runtime\cloudflared_stderr_*.log for details." -ForegroundColor Yellow
    if ($Tunnel -and -not $Tunnel.HasExited) {
        Stop-Process -Id $Tunnel.Id -Force -ErrorAction SilentlyContinue
    }
    return ""
}

function New-FrontendUrl {
    param([string]$BackendUrl)
    if (-not $BackendUrl) {
        return $PublicFrontendUrl
    }
    $Builder = [System.UriBuilder]::new($PublicFrontendUrl)
    $Builder.Query = "backend=$([System.Uri]::EscapeDataString($BackendUrl))"
    return $Builder.Uri.AbsoluteUri
}

function Write-ShareConfig {
    param(
        [string]$FrontendUrl,
        [string]$BackendUrl,
        [int]$Port
    )
    $LocalUrl = "http://127.0.0.1:$Port"
    $LanUrl = Get-LanUrl -Port $Port
    $Payload = [ordered]@{
        localUrl = $LocalUrl
        lanUrl = $LanUrl
        publicUrl = $FrontendUrl
        backendUrl = $BackendUrl
        preferredUrl = $FrontendUrl
        generatedAt = (Get-Date).ToString("o")
        source = "start_volleyform"
    }
    $Payload | ConvertTo-Json | Set-Content -LiteralPath $ShareConfig -Encoding UTF8
}

$BackendProcess = Start-BackendIfNeeded -Port $Port
$BackendUrl = Start-PublicBackendTunnel -Port $Port
$FrontendUrl = New-FrontendUrl -BackendUrl $BackendUrl
Write-ShareConfig -FrontendUrl $FrontendUrl -BackendUrl $BackendUrl -Port $Port

Write-Host ""
Write-Host "Opening open-source frontend:" -ForegroundColor Green
Write-Host $FrontendUrl -ForegroundColor Cyan
Write-Host "QR Code will use this public frontend URL, not 127.0.0.1." -ForegroundColor Cyan
Start-Process $FrontendUrl

Write-Host ""
Write-Host "Leave this computer on while using backend/tunnel features." -ForegroundColor Yellow
if ($BackendProcess) {
    Write-Host "Backend PID: $($BackendProcess.Id)" -ForegroundColor DarkGray
}
