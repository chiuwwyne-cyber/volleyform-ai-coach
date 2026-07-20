$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$FrontendSync = Join-Path $Root "tools\sync_frontend.py"
$BuildInfo = Join-Path $Root "frontend\build-info.json"
$ShareConfig = Join-Path $Root "frontend\runtime-share.json"
$PublicFrontendUrl = "https://chiuwwyne-cyber.github.io/volleyform-ai-coach/"
$SessionId = Get-Date -Format "yyyyMMddHHmmss"
$DesktopLatestShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "VolleyForm 本次網址.url"

function Get-AppBuildVersion {
    try {
        if (Test-Path $BuildInfo) {
            $Info = Get-Content -LiteralPath $BuildInfo -Raw | ConvertFrom-Json
            if ($Info.buildVersion) {
                return [string]$Info.buildVersion
            }
        }
    }
    catch {}
    try {
        $Git = Get-Command git -ErrorAction SilentlyContinue
        if ($Git) {
            $Commit = (& $Git.Source -C $Root rev-parse --short HEAD 2>$null).Trim()
            if ($Commit) {
                return $Commit
            }
        }
    }
    catch {}
    return Get-Date -Format "yyyyMMddHHmmss"
}

if (-not (Test-Path $Python)) {
    Write-Host "Cannot find .venv Python. Please install requirements first." -ForegroundColor Red
    exit 1
}

if (Test-Path $FrontendSync) {
    & $Python $FrontendSync --quiet
}

$BuildVersion = Get-AppBuildVersion

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

function New-FrontendUrl {
    param(
        [string]$SessionId,
        [string]$BuildVersion
    )
    $Builder = [System.UriBuilder]::new($PublicFrontendUrl)
    $Builder.Query = @(
        "session=$([System.Uri]::EscapeDataString($SessionId))",
        "build=$([System.Uri]::EscapeDataString($BuildVersion))"
    ) -join "&"
    return $Builder.Uri.AbsoluteUri
}

function Write-DesktopLatestUrl {
    param([string]$FrontendUrl)
    try {
        $ShortcutContent = "[InternetShortcut]`r`nURL=$FrontendUrl`r`n"
        Set-Content -LiteralPath $DesktopLatestShortcut -Value $ShortcutContent -Encoding ASCII
        Write-Host "Updated desktop latest URL shortcut: $DesktopLatestShortcut" -ForegroundColor Cyan
    }
    catch {
        Write-Host "Could not update the desktop latest URL shortcut. The app can still open normally." -ForegroundColor Yellow
    }
}

function Write-ShareConfig {
    param(
        [string]$PublicUrl = "",
        [string]$SessionId,
        [string]$BuildVersion,
        [int]$Port = 8000
    )
    $LocalUrl = "http://127.0.0.1:$Port"
    $LanUrl = Get-LanUrl -Port $Port
    $PreferredUrl = if ($PublicUrl) { $PublicUrl } elseif ($LanUrl -notlike "*127.0.0.1*") { $LanUrl } else { $PublicFrontendUrl }
    $Payload = [ordered]@{
        localUrl = $LocalUrl
        lanUrl = $LanUrl
        openSourceFrontendUrl = $PublicFrontendUrl
        publicUrl = $PublicUrl
        preferredUrl = $PreferredUrl
        sessionId = $SessionId
        buildVersion = $BuildVersion
        desktopLatestUrl = $DesktopLatestShortcut
        generatedAt = (Get-Date).ToString("o")
        source = "run_web_app"
    }
    $Payload | ConvertTo-Json | Set-Content -LiteralPath $ShareConfig -Encoding UTF8
    return $PreferredUrl
}

function Open-App {
    $Url = New-FrontendUrl -SessionId $SessionId -BuildVersion $BuildVersion
    Write-ShareConfig -PublicUrl $Url -SessionId $SessionId -BuildVersion $BuildVersion -Port 8000 | Out-Null
    Write-DesktopLatestUrl -FrontendUrl $Url
    Start-Process $Url
}

function Test-RunningBackendStale {
    param([int]$Port = 8000)
    try {
        $Conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop | Select-Object -First 1
        if (-not $Conn) { return $false }
        $Process = Get-Process -Id $Conn.OwningProcess -ErrorAction SilentlyContinue
        if (-not $Process) { return $false }
        $Started = $Process.StartTime
        $Newest = [DateTime]::MinValue
        foreach ($Dir in @("backend", "angle", "pose", "action", "tools")) {
            $Full = Join-Path $Root $Dir
            if (-not (Test-Path $Full)) { continue }
            $Files = Get-ChildItem -LiteralPath $Full -Recurse -File -Include "*.py", "*.json" -ErrorAction SilentlyContinue |
                Where-Object { $_.FullName -notmatch "__pycache__" }
            foreach ($File in $Files) {
                if ($File.LastWriteTime -gt $Newest) { $Newest = $File.LastWriteTime }
            }
        }
        if ($Newest -gt $Started) {
            Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 800
            return $true
        }
    }
    catch {}
    return $false
}

try {
    $Health = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 1 -UseBasicParsing -ErrorAction Stop
    if ($Health.StatusCode -eq 200) {
        if (Test-RunningBackendStale -Port 8000) {
            Write-Host "Backend code changed; restarting the server to load the latest code..." -ForegroundColor Yellow
        }
        else {
            Write-Host "Backend is already running the current code. Opening the app..." -ForegroundColor Green
            Open-App
            exit 0
        }
    }
}
catch {}

Write-Host "Starting Volleyball AI Coach backend..." -ForegroundColor Green
Write-Host "Your browser will open automatically once the server is ready." -ForegroundColor Cyan
Write-Host "Use the 'Generate QR code' button on the public frontend; it will not use 127.0.0.1." -ForegroundColor Cyan
Write-Host "For backend-powered analysis on different networks, use VolleyForm.bat so it can create a public backend tunnel." -ForegroundColor Cyan

$FrontendUrl = New-FrontendUrl -SessionId $SessionId -BuildVersion $BuildVersion
$ShareUrl = Write-ShareConfig -PublicUrl $FrontendUrl -SessionId $SessionId -BuildVersion $BuildVersion -Port 8000
Write-DesktopLatestUrl -FrontendUrl $FrontendUrl
Write-Host "Open-source frontend: $FrontendUrl" -ForegroundColor Cyan
Write-Host "Same-Wi-Fi backend URL: $ShareUrl" -ForegroundColor Cyan

$OpenBrowserJob = Start-Job -ScriptBlock {
    param($Url)
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 250
        try {
            $Response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 1 -UseBasicParsing
            if ($Response.StatusCode -eq 200) {
                Start-Process $Url
                break
            }
        }
        catch {}
    }
} -ArgumentList $FrontendUrl

try {
    & $Python (Join-Path $Root "backend\server.py") --host 0.0.0.0 --port 8000
}
finally {
    Stop-Job $OpenBrowserJob -ErrorAction SilentlyContinue | Out-Null
    Remove-Job $OpenBrowserJob -Force -ErrorAction SilentlyContinue | Out-Null
}
