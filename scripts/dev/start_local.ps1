param(
    [string]$HostName = "127.0.0.1",
    [int]$ApiPort = 8000,
    [int]$WebPort = 5173
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$apiRoot = Join-Path $repoRoot "apps\api"
$webRoot = Join-Path $repoRoot "apps\web"
$logDir = Join-Path $PSScriptRoot "logs"
$pidDir = Join-Path $PSScriptRoot ".pids"

New-Item -ItemType Directory -Path $logDir -Force | Out-Null
New-Item -ItemType Directory -Path $pidDir -Force | Out-Null

foreach ($name in @("api", "worker", "web")) {
    $pidFile = Join-Path $pidDir "$name.pid"
    if (Test-Path $pidFile) {
        $existingPid = Get-Content $pidFile | Select-Object -First 1
        if ($existingPid) {
            Stop-Process -Id ([int]$existingPid) -Force -ErrorAction SilentlyContinue
        }
        Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    }
}

$env:VSL_POSTGRES_USER = if ($env:VSL_POSTGRES_USER) { $env:VSL_POSTGRES_USER } else { "vsl_uat" }
$env:VSL_POSTGRES_PASSWORD = if ($env:VSL_POSTGRES_PASSWORD) { $env:VSL_POSTGRES_PASSWORD } else { "vsl_uat_local_password" }
$env:VSL_POSTGRES_DB = if ($env:VSL_POSTGRES_DB) { $env:VSL_POSTGRES_DB } else { "vsl_uat" }
$env:VSL_JWT_SECRET = if ($env:VSL_JWT_SECRET) { $env:VSL_JWT_SECRET } else { "local-dev-jwt-secret" }
$env:VSL_DATABASE_URL = if ($env:VSL_DATABASE_URL) { $env:VSL_DATABASE_URL } else { "postgresql+psycopg://$($env:VSL_POSTGRES_USER):$($env:VSL_POSTGRES_PASSWORD)@localhost:5432/$($env:VSL_POSTGRES_DB)" }
$env:VSL_REDIS_URL = if ($env:VSL_REDIS_URL) { $env:VSL_REDIS_URL } else { "redis://localhost:6379/0" }
$env:VSL_CELERY_BROKER_URL = if ($env:VSL_CELERY_BROKER_URL) { $env:VSL_CELERY_BROKER_URL } else { $env:VSL_REDIS_URL }
$env:VSL_CELERY_RESULT_BACKEND = if ($env:VSL_CELERY_RESULT_BACKEND) { $env:VSL_CELERY_RESULT_BACKEND } else { $env:VSL_REDIS_URL }
$env:VSL_CORS_ORIGINS = if ($env:VSL_CORS_ORIGINS) { $env:VSL_CORS_ORIGINS } else { "http://localhost:$WebPort,http://127.0.0.1:$WebPort" }
$env:VITE_API_BASE_URL = "http://$HostName`:$ApiPort"
$env:PYTHONPATH = ".tools/python;."

$nodeBin = "C:\Users\Sandman\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin"
if (Test-Path $nodeBin) {
    $env:PATH = "$nodeBin;$env:PATH"
}

Write-Host "Starting DB and Redis..." -ForegroundColor Cyan
Push-Location $repoRoot
try {
    docker compose up -d db redis
} finally {
    Pop-Location
}

Write-Host "Running migrations and seed..." -ForegroundColor Cyan
Push-Location $apiRoot
try {
    python -m alembic upgrade head
    python ..\..\scripts\data\import_kaoyan_syllabus.py
    python ..\..\scripts\uat\seed_demo_data.py
} finally {
    Pop-Location
}

Write-Host "Starting API, worker, and web dev server..." -ForegroundColor Cyan

$api = Start-Process -FilePath "python" `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", $HostName, "--port", "$ApiPort") `
    -WorkingDirectory $apiRoot `
    -RedirectStandardOutput (Join-Path $logDir "api.out.log") `
    -RedirectStandardError (Join-Path $logDir "api.err.log") `
    -PassThru `
    -WindowStyle Hidden

$worker = Start-Process -FilePath "python" `
    -ArgumentList @("-m", "celery", "-A", "app.domain.generation.tasks.celery_app", "worker", "--pool=solo", "--loglevel=INFO") `
    -WorkingDirectory $apiRoot `
    -RedirectStandardOutput (Join-Path $logDir "worker.out.log") `
    -RedirectStandardError (Join-Path $logDir "worker.err.log") `
    -PassThru `
    -WindowStyle Hidden

$web = Start-Process -FilePath "cmd.exe" `
    -ArgumentList @("/c", "node_modules\.bin\vite.cmd", "--host", $HostName, "--port", "$WebPort", "--strictPort") `
    -WorkingDirectory $webRoot `
    -RedirectStandardOutput (Join-Path $logDir "web.out.log") `
    -RedirectStandardError (Join-Path $logDir "web.err.log") `
    -PassThru `
    -WindowStyle Hidden

Set-Content -Path (Join-Path $pidDir "api.pid") -Value $api.Id
Set-Content -Path (Join-Path $pidDir "worker.pid") -Value $worker.Id
Set-Content -Path (Join-Path $pidDir "web.pid") -Value $web.Id

Write-Host ""
Write-Host "Local app is starting." -ForegroundColor Green
Write-Host "Frontend: http://$HostName`:$WebPort"
Write-Host "API:      http://$HostName`:$ApiPort/health/ready"
Write-Host "Invite:   DEMO2026"
Write-Host "Logs:     $logDir"
Write-Host ""
Write-Host "Stop with: powershell -ExecutionPolicy Bypass -File scripts\dev\stop_local.ps1"
