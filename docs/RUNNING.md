# Running NAVIXA AI locally (native, no Docker)

This environment does not have the `docker` CLI available, so all services run as
native Windows processes instead of via `docker/docker-compose.yml`. Keep this file
updated whenever the local dev startup process changes (new service, new env var,
new port, etc).

## Prerequisites (already running as standing services on this machine)

These are **not** started/stopped by app dev workflow — they're long-running local
services independent of this repo:

| Service | Port | Notes |
|---|---|---|
| PostgreSQL | 5432 | native Windows install, not the `postgres_data` docker volume |
| Redis | 6379 | native Windows install |
| Neo4j | 7474 (HTTP), 7687 (Bolt) | native Windows install |

Verify they're up before starting the app:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 5432,6379,7687
```

If any are down, they need to be started via their own Windows service/process —
that is outside this repo's scope.

## Config

- Backend env file: `backend/.env` (already present, copied/adapted from
  `.env.example` — not committed to git). Confirm `DATABASE_URL`, `REDIS_URL`,
  `NEO4J_URI` point at `localhost` (not the `postgres`/`redis`/`neo4j` docker
  hostnames used in `.env.example`, since we're not running docker-compose here).

## Start order

1. Postgres / Redis / Neo4j (prerequisite services above — confirm already running)
2. Backend API (uvicorn)
3. Celery worker
4. Celery beat
5. Frontend (Vite)

### 1. Backend API

```bash
cd backend
.venv/Scripts/uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload \
  > uvicorn_out.log 2> uvicorn_err.log &
```

- Serves at http://localhost:8000, docs at http://localhost:8000/docs
- Logs: `backend/uvicorn_out.log` (access log), `backend/uvicorn_err.log` (startup/reload log)

### 2. Celery worker

```bash
cd backend
.venv/Scripts/python.exe -m celery -A app.workers.celery_app worker --pool=solo --loglevel=info \
  > celery_worker.log 2> celery_worker_err.log &
```

- `--pool=solo` is required on Windows (the default prefork pool doesn't work).
- Handles `navixa.run_discovery` and `navixa.check_scheduled_discoveries` tasks.

### 3. Celery beat

```bash
cd backend
.venv/Scripts/python.exe -m celery -A app.workers.celery_app beat --loglevel=info \
  > celery_beat.log 2> celery_beat_err.log &
```

- Drives NAVIXA Watch's scheduled-discovery polling. Without this, `ScheduledDiscovery`
  rows are created but never fire (see comment in `docker/docker-compose.yml`).

### 4. Frontend

```bash
cd frontend
npm run dev > frontend.log 2>&1 &
```

- Vite picks the first free port starting at 5173; on this machine that's usually
  **5180** (5173 is taken by an unrelated project's dev server — see below).
  Check `frontend.log` / `frontend/vite_out.log` for the actual `Local:` URL.

## Verifying everything is up

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/docs   # expect 200
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:<vite-port>/  # expect 200
```

## Stopping everything

Find PIDs and stop them (PowerShell):

```powershell
Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -match 'uvicorn|celery_app|vite'
} | Select-Object ProcessId, CommandLine

Stop-Process -Id <pid1>,<pid2>,... -Force
```

Do **not** stop the Postgres/Redis/Neo4j processes (5432/6379/7687) unless you
specifically intend to take those services down — they're shared, standing
services, not part of this repo's dev-server lifecycle.

## Known gotchas

- **Port collision with an unrelated project.** This machine also runs a
  `portfolio-manager` project whose frontend Vite dev server claims port 5173
  first. NAVIXA AI's frontend then falls back to the next free port (5180 as of
  2026-07-04). Always check the actual `Local:` URL Vite prints rather than
  assuming 5173.
- **No `docker` CLI in this environment.** `docker/docker-compose.yml` describes
  the intended container topology but isn't usable for local dev here — services
  are started natively as described above instead.
