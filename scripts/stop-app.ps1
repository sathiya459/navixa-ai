<#
.SYNOPSIS
    Stops the processes started by start-app.ps1 (backend, Celery worker, frontend).

.DESCRIPTION
    Does NOT stop Postgres/Redis - those are standing services on this
    machine, not part of this repo's process lifecycle (see docs/RUNNING.md).

.USAGE
    powershell -ExecutionPolicy Bypass -File scripts/stop-app.ps1
#>

$PidFile = Join-Path $PSScriptRoot ".navixa-pids.json"

Write-Host "==================================================================" -ForegroundColor Yellow
Write-Host " NAVIXA AI - Stopping local dev stack" -ForegroundColor Yellow
Write-Host "==================================================================" -ForegroundColor Yellow

if (Test-Path $PidFile) {
    $serviceIds = Get-Content $PidFile | ConvertFrom-Json
    foreach ($name in @("backend", "celery_worker", "frontend")) {
        $procId = $serviceIds.$name
        if (-not $procId) { continue }
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($proc) {
            # taskkill /T kills the whole process tree, not just this PID -
            # needed for frontend, since "npm run dev" spawns cmd.exe ->
            # node vite.js, and Stop-Process alone only kills the
            # top-level npm process, leaving the actual Vite server running.
            taskkill /F /T /PID $procId | Out-Null
            Write-Host "Stopped $name (PID $procId, and its child processes)" -ForegroundColor Green
        } else {
            Write-Host "$name (PID $procId) was already stopped" -ForegroundColor DarkGray
        }
    }
} else {
    Write-Host ""
    Write-Host "No $PidFile found - falling back to the catch-all process sweep below." -ForegroundColor DarkGray
}

# uvicorn --reload's actual server is a spawned multiprocessing child that
# doesn't have "uvicorn" in its command line and can outlive its parent -
# see the "orphaned reload worker" gotcha in docs/INFRASTRUCTURE.md.
$orphans = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -match "multiprocessing.spawn" -and $_.CommandLine -match "spawn_main"
}
foreach ($orphan in $orphans) {
    Stop-Process -Id $orphan.ProcessId -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped orphaned reload worker (PID $($orphan.ProcessId))" -ForegroundColor Green
}

# Catch-all safety net: anything still matching our process signatures that
# the PID file didn't account for (e.g. a leftover Vite child tree).
$leftovers = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -match "uvicorn" -or
    $_.CommandLine -match "celery_app" -or
    $_.CommandLine -match "vite\.js" -or
    ($_.CommandLine -match "cmd.exe" -and $_.CommandLine -match "vite")
}
foreach ($leftover in $leftovers) {
    Stop-Process -Id $leftover.ProcessId -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped leftover process (PID $($leftover.ProcessId)): $($leftover.CommandLine)" -ForegroundColor Green
}

# Final safety net: kill whatever actually owns the ports we care about.
# CIM/WMI process queries have been observed to miss live processes that
# Get-Process finds (a Windows quirk, not specific to this app) - checking
# by port ownership is the most reliable signal that something is still
# actually serving traffic, regardless of how its command line looks.
foreach ($port in @(8000) + (5173..5190)) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($conn in $conns) {
        $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
        if ($proc) {
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
            Write-Host "Stopped process still listening on port ${port} (PID $($conn.OwningProcess))" -ForegroundColor Green
        }
    }
}

Remove-Item $PidFile -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Done. Postgres/Redis were left running (standing services, not managed here)." -ForegroundColor Yellow
