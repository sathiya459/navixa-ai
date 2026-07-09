# Running NAVIXA AI locally (native, no Docker)

This environment does not have the `docker` CLI available, so all services run as
native Windows processes instead of via `docker/docker-compose.yml`. Keep this file
updated whenever the local dev startup process changes (new service, new env var,
new port, etc).

## Prerequisites (already running as standing services on this machine)

These are **not** started/stopped by app dev workflow — they're long-running local
services independent of this repo:

| Service | Port | Windows service name | Notes |
|---|---|---|---|
| PostgreSQL (navixa_db) | **5433** | `navixa-postgresql-5433` | native Windows install (`PostgreSQL/17`, data dir `c:/tools/pgdata`), not the `postgres_data` docker volume. This machine also runs an unrelated PostgreSQL instance on the standard 5432 (Windows service `postgresql-x64-17`) — don't confuse the two; `backend/.env`'s `DATABASE_URL` is the source of truth for which port the app actually uses. |
| Redis | 6379 | `navixa-redis` | native Windows install at `c:/tools/redis`, used only as the Celery broker/result backend |

Both are registered as Windows services with **Automatic** startup type, so they
come up on their own after a system reboot — no manual start needed in the normal
case.

Verify they're up before starting the app:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 5433,6379
```

If either is down, start it via its service:

```powershell
Start-Service navixa-postgresql-5433
Start-Service navixa-redis
```

(They were originally set up as ad-hoc processes — `pg_ctl start` /
`redis-server.exe redis.windows.conf` — then registered as services via
`pg_ctl register` and `redis-server --service-install` so they'd survive
reboots.)

## Config

- Backend env file: `backend/.env` (already present, copied/adapted from
  `.env.example` — not committed to git). Confirm `DATABASE_URL`/`REDIS_URL`
  point at `localhost` (not the `postgres`/`redis` docker hostnames used in
  `.env.example`, since we're not running docker-compose here).

## Start order

1. Postgres / Redis (prerequisite services above — confirm already running)
2. Backend API (uvicorn)
3. Celery worker
4. Frontend (Vite)

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
- Handles `navixa.run_discovery`, the on-demand NAVIXA Discover task. There is no
  Celery beat process — NAVIXA Watch (scheduled/recurring discovery) has been removed.

### 3. Frontend

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

Do **not** stop the Postgres/Redis processes (5433/6379) unless you
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
- **`backend/.env` must actually be found to take effect.** `Settings`
  (`app/config/settings.py`) now resolves `.env` via an absolute path
  (`Path(__file__).resolve().parents[2] / ".env"`), so it loads correctly
  regardless of the process's working directory. Before this fix, a
  relative `env_file=".env"` meant any launch method that didn't `cd
  backend` first (an IDE run config, a script invoked from the repo root,
  etc.) would silently fail to find it and fall back to every field's
  hardcoded class default — including `database_url` pointing at port 5432
  with generic `navixa:navixa` credentials instead of the real local
  Postgres on 5433 — with no error raised. If the app ever appears to be
  talking to the wrong Postgres port/credentials again, suspect this class
  of bug first: check `GET /api/v1/...` behavior against `Settings().database_url`
  printed directly, not just assumed from `.env`'s contents.
- **Orphaned `uvicorn --reload` worker processes can silently keep serving
  stale code.** See "Known operational gotchas" in
  [docs/INFRASTRUCTURE.md](INFRASTRUCTURE.md) — the actual server process
  spawned by `--reload` doesn't have `"uvicorn"` in its command line, so a
  process search/kill filtered on that string can miss a stale instance
  from an earlier session that's still bound to the port.
- **Celery does not hot-reload.** The backend API runs with `--reload` (uvicorn
  watches files and restarts itself), but the Celery worker process does
  not — it keeps executing whatever code was loaded at its own startup,
  indefinitely. After editing anything under `app/collectors/`, `app/workers/`,
  or `app/tenant_registry/`, you must manually kill and restart the worker
  (see "Stopping everything" above, filtering to `celery_app`), or NAVIXA
  Discover jobs will silently keep running the old code with no indication
  anything is stale. This has caused confusing "my fix didn't work" symptoms
  more than once — always check the worker's startup banner timestamp in
  `celery_worker.log` against the mtime of the files you changed before
  concluding a fix doesn't work.
