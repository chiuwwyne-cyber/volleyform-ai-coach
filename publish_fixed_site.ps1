param(
    [string]$Repository = "volleyform-ai-coach",
    [string]$BackendUrl = ""
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Git = Join-Path $Root "tools\portable\git\cmd\git.exe"
$Gh = Join-Path $Root "tools\portable\gh\bin\gh.exe"
$SafeDirectory = $Root.Replace("\", "/")

if (-not (Test-Path $Git) -or -not (Test-Path $Gh)) {
    Write-Host "Portable Git tools are missing." -ForegroundColor Red
    exit 1
}

& $Gh auth status
if ($LASTEXITCODE -ne 0) {
    Write-Host "Please finish GitHub login first:" -ForegroundColor Yellow
    Write-Host ".\tools\portable\gh\bin\gh.exe auth login --hostname github.com --git-protocol https --web" -ForegroundColor Cyan
    exit 1
}

$Status = & $Git -c "safe.directory=$SafeDirectory" status --porcelain
if ($Status) {
    Write-Host "The repository has uncommitted changes. Commit them before publishing." -ForegroundColor Red
    exit 1
}

$Login = (& $Gh api user --jq .login).Trim()
$FullRepository = "$Login/$Repository"

$Remote = & $Git -c "safe.directory=$SafeDirectory" remote get-url origin 2>$null
if (-not $Remote) {
    Write-Host "Creating public repository $FullRepository ..." -ForegroundColor Green
    & $Gh repo create $FullRepository --public --source $Root --remote origin --push `
        --description "Open-source 3D volleyball motion analysis and mobile AI coaching."
}
else {
    Write-Host "Pushing the current main branch..." -ForegroundColor Green
    & $Git -c "safe.directory=$SafeDirectory" push -u origin main
}

if ($BackendUrl) {
    $NormalizedBackend = $BackendUrl.TrimEnd("/")
    & $Gh variable set BACKEND_URL --repo $FullRepository --body $NormalizedBackend
    Write-Host "Configured BACKEND_URL: $NormalizedBackend" -ForegroundColor Green
}
else {
    Write-Host "BACKEND_URL is empty. The fixed UI will publish, but analysis needs a public backend URL." -ForegroundColor Yellow
}

$PagesExists = $true
& $Gh api "repos/$FullRepository/pages" *> $null
if ($LASTEXITCODE -ne 0) {
    $PagesExists = $false
}

if (-not $PagesExists) {
    & $Gh api --method POST "repos/$FullRepository/pages" -f build_type=workflow *> $null
}

& $Gh workflow run pages.yml --repo $FullRepository

Write-Host "Fixed site deployment started." -ForegroundColor Green
Write-Host "Repository: https://github.com/$FullRepository" -ForegroundColor Cyan
Write-Host "Website: https://$Login.github.io/$Repository/" -ForegroundColor Cyan
