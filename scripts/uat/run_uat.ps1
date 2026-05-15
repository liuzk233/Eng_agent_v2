# UAT Runner for vocabulary-story-learning
# Usage: powershell -ExecutionPolicy Bypass -File scripts/uat/run_uat.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== WordFlow UAT Runner ===" -ForegroundColor Cyan

$repoRoot = (Get-Location).Path
$apiProcess = $null
$workerProcess = $null

$env:VSL_POSTGRES_USER = if ($env:VSL_POSTGRES_USER) { $env:VSL_POSTGRES_USER } else { "vsl_uat" }
$env:VSL_POSTGRES_PASSWORD = if ($env:VSL_POSTGRES_PASSWORD) { $env:VSL_POSTGRES_PASSWORD } else { "vsl_uat_local_password" }
$env:VSL_POSTGRES_DB = if ($env:VSL_POSTGRES_DB) { $env:VSL_POSTGRES_DB } else { "vsl_uat" }
$env:VSL_JWT_SECRET = if ($env:VSL_JWT_SECRET) { $env:VSL_JWT_SECRET } else { "uat-local-jwt-secret-change-me" }
$env:VSL_REDIS_URL = if ($env:VSL_REDIS_URL) { $env:VSL_REDIS_URL } else { "redis://localhost:6379/0" }
$env:VSL_CELERY_BROKER_URL = if ($env:VSL_CELERY_BROKER_URL) { $env:VSL_CELERY_BROKER_URL } else { $env:VSL_REDIS_URL }
$env:VSL_CELERY_RESULT_BACKEND = if ($env:VSL_CELERY_RESULT_BACKEND) { $env:VSL_CELERY_RESULT_BACKEND } else { $env:VSL_REDIS_URL }
$env:VSL_UAT_ADMIN_ACCOUNT = if ($env:VSL_UAT_ADMIN_ACCOUNT) { $env:VSL_UAT_ADMIN_ACCOUNT } else { "uat-admin-$([guid]::NewGuid().ToString('N').Substring(0, 8))@wordflow.test" }
$env:VSL_UAT_ADMIN_PASSWORD = if ($env:VSL_UAT_ADMIN_PASSWORD) { $env:VSL_UAT_ADMIN_PASSWORD } else { [guid]::NewGuid().ToString("N") }
$databaseUrl = "postgresql+psycopg://$($env:VSL_POSTGRES_USER):$($env:VSL_POSTGRES_PASSWORD)@localhost:5432/$($env:VSL_POSTGRES_DB)"
$nodeBin = "C:\Users\Sandman\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin"
if (Test-Path $nodeBin) {
    $env:PATH = "$nodeBin;$env:PATH"
}

Write-Host "`n[1/6] Starting Docker services..." -ForegroundColor Yellow
docker compose up -d db redis
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker services failed to start. Is Docker Desktop running?" -ForegroundColor Red
    exit $LASTEXITCODE
}
Start-Sleep -Seconds 5

Write-Host "`n[2/6] Running database migrations..." -ForegroundColor Yellow
Push-Location apps/api
try {
    $env:VSL_DATABASE_URL = $databaseUrl
    $env:PYTHONPATH = ".tools/python;."
    python -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Migration failed. Trying to create database..." -ForegroundColor Red
        $env:PGPASSWORD = $env:VSL_POSTGRES_PASSWORD
        createdb -h localhost -U $env:VSL_POSTGRES_USER $env:VSL_POSTGRES_DB 2>$null
        python -m alembic upgrade head
    }
} finally {
    Pop-Location
}

Write-Host "`n[3/6] Seeding demo data..." -ForegroundColor Yellow
Push-Location apps/api
try {
    $env:VSL_DATABASE_URL = $databaseUrl
    $env:PYTHONPATH = ".tools/python;."
    python ../../scripts/uat/seed_demo_data.py
} finally {
    Pop-Location
}

try {
    Write-Host "`n[4/6] Running backend tests..." -ForegroundColor Yellow
    Push-Location apps/api
    try {
        $env:PYTHONPATH = ".tools/python;."
        python -m pytest -q
        $backendResult = $LASTEXITCODE
    } finally {
        Pop-Location
    }

    Write-Host "`n[5/6] Running frontend tests..." -ForegroundColor Yellow
    Push-Location apps/web
    try {
        cmd /c node_modules\.bin\vitest.cmd --run --reporter=verbose
        $frontendResult = $LASTEXITCODE
    } finally {
        Pop-Location
    }

    Write-Host "`n[6/6] Running API-backed generation E2E..." -ForegroundColor Yellow
    $env:VSL_DATABASE_URL = $databaseUrl
    $env:PYTHONPATH = ".tools/python;."
    $env:VITE_API_BASE_URL = "http://127.0.0.1:8000"

    $apiOutLog = Join-Path $repoRoot "scripts/uat/api-server.out.log"
    $apiErrLog = Join-Path $repoRoot "scripts/uat/api-server.err.log"
    $workerOutLog = Join-Path $repoRoot "scripts/uat/celery-worker.out.log"
    $workerErrLog = Join-Path $repoRoot "scripts/uat/celery-worker.err.log"
    $apiProcess = Start-Process -FilePath "python" -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") -WorkingDirectory (Join-Path $repoRoot "apps/api") -RedirectStandardOutput $apiOutLog -RedirectStandardError $apiErrLog -PassThru -WindowStyle Hidden
    $workerProcess = Start-Process -FilePath "python" -ArgumentList @("-m", "celery", "-A", "app.domain.generation.tasks.celery_app", "worker", "--pool=solo", "--loglevel=INFO") -WorkingDirectory (Join-Path $repoRoot "apps/api") -RedirectStandardOutput $workerOutLog -RedirectStandardError $workerErrLog -PassThru -WindowStyle Hidden

    $apiReady = $false
    for ($i = 0; $i -lt 30; $i++) {
        try {
            Invoke-RestMethod -Uri "http://127.0.0.1:8000/health/ready" -TimeoutSec 2 | Out-Null
            $apiReady = $true
            break
        } catch {
            Start-Sleep -Seconds 1
        }
    }

    if (-not $apiReady) {
        Write-Host "API server did not become ready. See $apiOutLog and $apiErrLog" -ForegroundColor Red
        $e2eResult = 1
    } else {
        Push-Location $repoRoot
        try {
            cmd /c apps\web\node_modules\.bin\vitest.cmd --config apps\web\vite.e2e.config.ts --run tests\e2e\auth_story_generation.spec.ts --testTimeout=60000
            $e2eResult = $LASTEXITCODE
        } finally {
            Pop-Location
        }
    }
} finally {
    if ($apiProcess -and -not $apiProcess.HasExited) {
        Stop-Process -Id $apiProcess.Id -Force
    }
    if ($workerProcess -and -not $workerProcess.HasExited) {
        Stop-Process -Id $workerProcess.Id -Force
    }
}

Write-Host "`n=== UAT Summary ===" -ForegroundColor Cyan
Write-Host "Backend tests: $(if ($backendResult -eq 0) { 'PASSED' } else { 'FAILED' })"
Write-Host "Frontend tests: $(if ($frontendResult -eq 0) { 'PASSED' } else { 'FAILED' })"
Write-Host "Generation E2E: $(if ($e2eResult -eq 0) { 'PASSED' } else { 'FAILED' })"

if ($backendResult -eq 0 -and $frontendResult -eq 0 -and $e2eResult -eq 0) {
    Write-Host "`nAll UAT checks passed!" -ForegroundColor Green
    exit 0
}

Write-Host "`nSome UAT checks failed." -ForegroundColor Red
exit 1
