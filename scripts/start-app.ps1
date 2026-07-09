<#
.SYNOPSIS
    Starts NAVIXA AI's local dev stack: backend API, Celery worker, frontend.

.DESCRIPTION
    Prints what it's doing and why at each step, waits for each process to
    actually be ready (not just "launched") before moving on, and finishes
    with a summary once everything is confirmed up. Logs go to scripts/logs/
    so this terminal stays readable; PIDs are recorded to
    scripts/.navixa-pids.json for stop-app.ps1 to use.

    Does NOT start Postgres/Redis - those are standing services on this
    machine (see docs/RUNNING.md), not part of this repo's process lifecycle.

.USAGE
    powershell -ExecutionPolicy Bypass -File scripts/start-app.ps1
#>

$ErrorActionPreference = "Stop"

# Python buffers stdout when it isn't attached to a real console (true of
# Start-Process's redirected output), so log files can sit empty for a long
# time even though the process is already past the point we're waiting on.
# Unbuffered output makes redirected logs show up immediately.
$env:PYTHONUNBUFFERED = "1"

$RepoRoot   = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"
$LogDir     = Join-Path $PSScriptRoot "logs"
$PidFile    = Join-Path $PSScriptRoot ".navixa-pids.json"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Step($number, $title, $detail) {
    Write-Host ""
    Write-Host "[$number] $title" -ForegroundColor Cyan
    if ($detail) { Write-Host "    $detail" -ForegroundColor DarkGray }
}

function Write-Ok($message) {
    Write-Host "    OK: $message" -ForegroundColor Green
}

function Write-Fail($message) {
    Write-Host "    FAILED: $message" -ForegroundColor Red
}

function Test-Port($port) {
    $conn = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
    return [bool]$conn
}

function Wait-ForHttp($hostName, $port, $timeoutSeconds, $description) {
    # Uses a raw TCP connect rather than Invoke-WebRequest: on some machines
    # Invoke-WebRequest routes through a configured system proxy that
    # doesn't handle localhost, causing it to hang/fail even though the
    # server is genuinely up and reachable (confirmed via curl). A TCP
    # connect to the port is a sufficient readiness signal here and avoids
    # that entirely.
    $deadline = (Get-Date).AddSeconds($timeoutSeconds)
    $lastTick = Get-Date
    while ((Get-Date) -lt $deadline) {
        $client = New-Object System.Net.Sockets.TcpClient
        try {
            $async = $client.BeginConnect($hostName, $port, $null, $null)
            $connected = $async.AsyncWaitHandle.WaitOne(1000)
            if ($connected -and $client.Connected) { return $true }
        } catch {
        } finally {
            $client.Close()
        }
        if (((Get-Date) - $lastTick).TotalSeconds -ge 5) {
            Write-Host "    ... still waiting on $description" -ForegroundColor DarkGray
            $lastTick = Get-Date
        }
    }
    Write-Fail "$description did not become reachable on ${hostName}:${port} within ${timeoutSeconds}s"
    return $false
}

# Vite (and other CLI tools) colorize output with ANSI escape codes that
# land inside the very text we need to match (e.g. "Local" <esc> ":" ...
# "localhost:" <esc> "5180"), splitting literal substrings across escape
# sequences. Stripping them before matching avoids fragile regexes that
# try to tolerate arbitrary codes in the middle of a token.
function Strip-Ansi($text) {
    if ($null -eq $text) { return $text }
    return [regex]::Replace($text, "\x1b\[[0-9;]*[a-zA-Z]", "")
}

function Wait-ForLogPattern($logPaths, $pattern, $timeoutSeconds, $description) {
    $deadline = (Get-Date).AddSeconds($timeoutSeconds)
    $lastTick = Get-Date
    while ((Get-Date) -lt $deadline) {
        foreach ($logPath in $logPaths) {
            if (Test-Path $logPath) {
                $content = Strip-Ansi (Get-Content $logPath -Raw -ErrorAction SilentlyContinue)
                if ($content -match $pattern) { return $true }
            }
        }
        Start-Sleep -Milliseconds 500
        if (((Get-Date) - $lastTick).TotalSeconds -ge 5) {
            Write-Host "    ... still waiting on $description" -ForegroundColor DarkGray
            $lastTick = Get-Date
        }
    }
    Write-Fail "$description did not show '$pattern' in its log within ${timeoutSeconds}s"
    return $false
}

function Get-LogMatch($logPaths, $pattern) {
    foreach ($logPath in $logPaths) {
        if (Test-Path $logPath) {
            $content = Strip-Ansi (Get-Content $logPath -Raw -ErrorAction SilentlyContinue)
            $match = [regex]::Match($content, $pattern)
            if ($match.Success) { return $match }
        }
    }
    return $null
}

Write-Host "==================================================================" -ForegroundColor Yellow
Write-Host " NAVIXA AI - Starting local dev stack" -ForegroundColor Yellow
Write-Host "==================================================================" -ForegroundColor Yellow

# -------------------------------------------------------------------------
# Step 0: Prerequisite services (not managed by this script)
# -------------------------------------------------------------------------
Write-Step 0 "Checking prerequisite services" "Postgres and Redis are standing services on this machine - this script does not start them."

$postgresUp = Test-Port 5433
$redisUp = Test-Port 6379

if ($postgresUp) { Write-Ok "PostgreSQL is listening on port 5433" }
else { Write-Fail "PostgreSQL is NOT listening on port 5433 - start it before continuing (see docs/RUNNING.md)" }

if ($redisUp) { Write-Ok "Redis is listening on port 6379 (used as the Celery broker/result backend)" }
else { Write-Fail "Redis is NOT listening on port 6379 - start it before continuing (see docs/RUNNING.md)" }

if (-not ($postgresUp -and $redisUp)) {
    Write-Host ""
    Write-Host "Aborting: prerequisite services are down. Start them, then re-run this script." -ForegroundColor Red
    exit 1
}

$serviceIds = @{}

# -------------------------------------------------------------------------
# Step 1: Backend API
# -------------------------------------------------------------------------
Write-Step 1 "Starting Backend API" "Runs app/main.py via Uvicorn (python -m uvicorn app.main:app). Serves the /api/v1 HTTP surface the frontend and Celery both depend on."

$backendLog = Join-Path $LogDir "backend.log"
$backendErrLog = Join-Path $LogDir "backend.err.log"
Remove-Item $backendLog, $backendErrLog -ErrorAction SilentlyContinue
$backendProc = Start-Process -FilePath (Join-Path $BackendDir ".venv\Scripts\python.exe") `
    -ArgumentList "-u", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload" `
    -WorkingDirectory $BackendDir `
    -RedirectStandardOutput $backendLog `
    -RedirectStandardError $backendErrLog `
    -PassThru -WindowStyle Hidden

Write-Host "    Launched process PID $($backendProc.Id), waiting for it to accept requests..." -ForegroundColor DarkGray
Write-Host "    (First-run startup can take a while - Settings resolves secrets from Azure Key Vault.)" -ForegroundColor DarkGray
if (Wait-ForHttp "localhost" 8000 120 "Backend API") {
    Write-Ok "Backend API is up at http://localhost:8000 (docs: http://localhost:8000/docs)"
    $serviceIds["backend"] = $backendProc.Id
} else {
    Write-Host "    See $backendLog for details." -ForegroundColor Red
    exit 1
}

# -------------------------------------------------------------------------
# Step 2: Celery worker
# -------------------------------------------------------------------------
Write-Step 2 "Starting Celery worker" "Runs app/workers/tasks.py's navixa.run_discovery task via Celery, using Redis as the broker. This is what actually executes NAVIXA Discover jobs kicked off from the API - without it, jobs stay queued forever."

$celeryLog = Join-Path $LogDir "celery_worker.log"
$celeryErrLog = Join-Path $LogDir "celery_worker.err.log"
Remove-Item $celeryLog, $celeryErrLog -ErrorAction SilentlyContinue
$celeryProc = Start-Process -FilePath (Join-Path $BackendDir ".venv\Scripts\python.exe") `
    -ArgumentList "-u", "-m", "celery", "-A", "app.workers.celery_app", "worker", "--pool=solo", "--loglevel=info" `
    -WorkingDirectory $BackendDir `
    -RedirectStandardOutput $celeryLog `
    -RedirectStandardError $celeryErrLog `
    -PassThru -WindowStyle Hidden

Write-Host "    Launched process PID $($celeryProc.Id), waiting for it to connect to Redis..." -ForegroundColor DarkGray
if (Wait-ForLogPattern @($celeryLog, $celeryErrLog) "Connected to redis" 90 "Celery worker") {
    Write-Ok "Celery worker is connected to Redis and ready to process Discover jobs"
    $serviceIds["celery_worker"] = $celeryProc.Id
} else {
    Write-Host "    See $celeryLog for details." -ForegroundColor Red
    exit 1
}

# -------------------------------------------------------------------------
# Step 3: Frontend
# -------------------------------------------------------------------------
Write-Step 3 "Starting Frontend" "Runs Vite dev server (npm run dev) for the React app - the UI you interact with in the browser."

$frontendLog = Join-Path $LogDir "frontend.log"
$frontendErrLog = Join-Path $LogDir "frontend.err.log"
Remove-Item $frontendLog, $frontendErrLog -ErrorAction SilentlyContinue
$npmCmd = (Get-Command npm.cmd -ErrorAction SilentlyContinue)
if (-not $npmCmd) { $npmCmd = Get-Command npm -ErrorAction Stop }
$frontendProc = Start-Process -FilePath $npmCmd.Source `
    -ArgumentList "run", "dev" `
    -WorkingDirectory $FrontendDir `
    -RedirectStandardOutput $frontendLog `
    -RedirectStandardError $frontendErrLog `
    -PassThru -WindowStyle Hidden

Write-Host "    Launched process PID $($frontendProc.Id), waiting for Vite to bind a port..." -ForegroundColor DarkGray
$frontendLogs = @($frontendLog, $frontendErrLog)
if (Wait-ForLogPattern $frontendLogs "Local:\s*http://localhost:(\d+)" 30 "Frontend") {
    $match = Get-LogMatch $frontendLogs "Local:\s*http://localhost:(\d+)"
    $frontendPort = $match.Groups[1].Value
    Write-Ok "Frontend is up at http://localhost:$frontendPort"
    $serviceIds["frontend"] = $frontendProc.Id
} else {
    Write-Host "    See $frontendLog for details." -ForegroundColor Red
    exit 1
}

# -------------------------------------------------------------------------
# Done
# -------------------------------------------------------------------------
$serviceIds | ConvertTo-Json | Set-Content $PidFile

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host " NAVIXA AI is running" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host " Backend API : http://localhost:8000  (docs: /docs)" -ForegroundColor Green
Write-Host " Frontend    : http://localhost:$frontendPort" -ForegroundColor Green
Write-Host " Celery      : connected, processing Discover jobs in the background" -ForegroundColor Green
Write-Host ""
Write-Host " Logs: $LogDir" -ForegroundColor DarkGray
Write-Host " PIDs saved to: $PidFile" -ForegroundColor DarkGray
Write-Host " To stop everything: powershell -File scripts/stop-app.ps1" -ForegroundColor DarkGray
Write-Host "==================================================================" -ForegroundColor Green
