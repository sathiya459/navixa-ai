# Infrastructure & Dependencies

What has to exist and be running for NAVIXA AI to work, independent of any
one feature. For step-by-step start/stop commands in this dev environment,
see [docs/RUNNING.md](RUNNING.md); this file is the reference list of *what*
is required and *why*.

## Runtimes

| Runtime | Version used | Notes |
|---|---|---|
| Python | 3.12 (backend `.venv`) | `backend/requirements.txt` pins exact package versions. A stray non-venv Python on `PATH` (e.g. a `pythoncore-3.12-64` install) can shadow the venv interpreter if a process is launched without `.venv/Scripts/` explicitly — always invoke `.venv/Scripts/python.exe`/`uvicorn.exe`/etc. directly, not a bare `python`/`uvicorn`. |
| Node.js | 18+ (developed against v21) | Frontend build/dev server (Vite). |
| npm | 10+ | Comes with Node. |

## Backing services

These are stateful, long-running services the app depends on but does not
manage the lifecycle of itself. In this dev environment they run as native
Windows installs (see `docs/RUNNING.md`); `docker/docker-compose.yml`
describes the equivalent containerized versions for environments where
Docker is available.

| Service | Purpose | Default port(s) | Image (docker-compose) |
|---|---|---|---|
| PostgreSQL | Primary datastore — tenants, scopes, audit jobs, network resources, findings, reports, users/roles. Migrated via Alembic (`backend/alembic/`). | 5432 | `postgres:16-alpine` |
| Redis | Celery broker + result backend (task queue for NAVIXA Discover runs and NAVIXA Watch's scheduled-discovery polling). | 6379 | `redis:7-alpine` |
| Neo4j | NAVIXA Graph — persisted topology (`navixa_graph`), separate from Postgres's relational inventory. Requires the `apoc` plugin unrestricted (`NEO4J_dbms_security_procedures_unrestricted: apoc.*`). In this dev environment it's managed via **Neo4j Desktop**, not a Windows service — someone has to open the app and start the DBMS manually; there's no CLI/headless start path here. If it's down, Discover jobs still complete (Neo4j sync failures are caught, see `graph_engine/writer.py`) but the Topology page shows empty/failed until a manual re-sync (`POST /graph/jobs/{id}/sync`, or the "Sync Topology to Graph" button). | 7474 (HTTP), 7687 (Bolt) | `neo4j:5-community` |

## Application processes

Run by/for this repo, not shared standing services:

| Process | Depends on | Notes |
|---|---|---|
| Backend API (`uvicorn app.main:app`) | Postgres, Redis (for enqueuing), Neo4j (soft dependency — degrades gracefully if down) | `--reload` in dev. See the "orphaned reload worker" gotcha below. |
| Celery worker (`celery -A app.workers.celery_app worker --pool=solo`) | Postgres, Redis, Neo4j, cloud provider credentials | Runs `navixa.run_discovery` (NAVIXA Discover) and `navixa.check_scheduled_discoveries`. `--pool=solo` is required on Windows. **Does not hot-reload** — must be manually restarted after editing `app/collectors/`, `app/workers/`, or `app/tenant_registry/`. |
| Celery beat (`celery -A app.workers.celery_app beat`) | Redis | Drives NAVIXA Watch's scheduled-discovery polling on a timer. Without it, `ScheduledDiscovery` rows exist but never fire. |
| Frontend (`vite`) | Backend API reachable at `VITE_API_BASE_URL` | Dev server; no separate backing service. |

## External/optional dependencies

- **AI providers** (NAVIXA InsightAI, `ai_engine/`): Anthropic, OpenAI, Azure OpenAI, Gemini, or AWS Bedrock. At least one needs an API key configured (`ANTHROPIC_API_KEY` etc. in `.env`) for AI-assisted insights, deviation detection (`analysis_mode=ai`), and topology explanations to work — the rest of the app functions without any of them configured.
- **Cloud provider credentials** (NAVIXA Discover, `collectors/`): AWS (IAM role assumption via `AWS_AUDIT_ROLE_NAME`/`AWS_AUDIT_EXTERNAL_ID`, or a local `AWS_PROFILE`), Azure (federated app credentials via `AZURE_FEDERATION_*`, or delegated SSO), GCP (`GCP_AUDIT_SERVICE_ACCOUNT`), OCI (`OCI_CONFIG_PROFILE`/session token). Only the providers actually being audited need credentials configured.
- **Entra ID (Azure AD) SSO** (`ENTRA_TENANT_ID`/`ENTRA_CLIENT_ID`/`ENTRA_CLIENT_SECRET`): optional — unset keeps local JWT email/password login as the only auth path.
- **Secret Manager** (`SECRET_PROVIDER`): `env` (default, reads secrets straight from `.env`/real env vars — fine for local dev) or `azure_key_vault`/`aws_secrets_manager` for production, so real secrets never live in a checked-out `.env`. Expected vault secret names are listed in `.env.example`.

## Required environment variables

See `backend/.env.example` for the full annotated list (never commit a real
`.env`). At minimum for local dev: `DATABASE_URL`, `REDIS_URL`, `NEO4J_URI`/
`NEO4J_USER`/`NEO4J_PASSWORD`, `JWT_SECRET_KEY`, `CORS_ORIGINS`. Everything
else (AI provider keys, cloud credentials, Entra SSO, Secret Manager) is
optional and only gates the specific feature it backs.

Frontend: `frontend/.env` needs `VITE_API_BASE_URL` pointing at the backend
API (e.g. `http://localhost:8000/api/v1`).

## Known operational gotchas

- **Neo4j has no headless start in this environment.** It must be started
  via Neo4j Desktop's UI before Discover/Topology-dependent work; there's no
  service or CLI command to bring it up unattended here.
- **Orphaned `uvicorn --reload` worker processes.** On Windows, `uvicorn
  --reload`'s actual server process is a `multiprocessing.spawn` child whose
  command line is just `python -c "from multiprocessing.spawn import
  spawn_main; ..."` — it does **not** contain the string `"uvicorn"`. A
  process search/kill filtered on `-match 'uvicorn'` will silently miss it,
  so a stale worker from an earlier session can keep answering requests on
  port 8000 with old code even after starting a fresh instance (which may
  successfully bind the "same" port anyway). If a fix doesn't seem to take
  effect despite the source file being correct, check `GET /openapi.json`
  against the running port for the actual registered routes, and search
  processes by the `spawn_main(parent_pid=...)` pattern too, not just image
  name/command substring.
- **Celery does not hot-reload** (see table above) — a common source of
  "my fix didn't work" confusion; always restart worker/beat after touching
  their code paths.
- **Port collision with an unrelated project.** This machine also runs
  another project's Vite dev server on 5173; NAVIXA AI's frontend falls back
  to the next free port (5180 as of this writing). Check the actual
  `Local:` URL Vite prints.
