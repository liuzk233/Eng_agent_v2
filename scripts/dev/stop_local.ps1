$ErrorActionPreference = "SilentlyContinue"

$pidDir = Join-Path $PSScriptRoot ".pids"

foreach ($name in @("api", "worker", "web")) {
    $pidFile = Join-Path $pidDir "$name.pid"
    if (Test-Path $pidFile) {
        $processId = Get-Content $pidFile | Select-Object -First 1
        if ($processId) {
            Stop-Process -Id ([int]$processId) -Force
            Write-Host "Stopped $name ($processId)"
        }
        Remove-Item -LiteralPath $pidFile -Force
    }
}

Write-Host "Stopped local API, worker, and web processes."
Write-Host "DB/Redis containers are left running. Stop them with: docker compose stop db redis"
