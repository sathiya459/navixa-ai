# NAVIXA AI — Project Documentation

NAVIXA AI is an AI-powered multi-cloud network architecture visibility and exposure analytics platform. It discovers cloud network inventory (AWS/Azure/GCP/OCI), stores it as a graph, validates it against hub-and-spoke compliance rules, analyzes internet exposure, generates AI-assisted insights, tracks changes over time, and produces reports.

## Stack

- **Backend**: FastAPI 0.115 + Uvicorn, Pydantic v2, SQLAlchemy 2.0 + Alembic (Postgres via psycopg3), Celery 5 + Redis, Neo4j (graph storage), NetworkX (in-memory graph algorithms), cloud SDKs (aioboto3, azure-identity/mgmt, google-cloud-compute, oci), AI SDKs (anthropic, openai, google-generativeai), MSAL (Entra ID SSO), jose/passlib/bcrypt (auth), fpdf2/openpyxl/jinja2 (reports).
- **Frontend**: Vite 5 + React 18 + TypeScript 5.6, React Router v7, MUI v9 + Emotion, axios, reactflow (topology diagrams). No dedicated state library — React Context + local state.

## Running locally

See [docs/RUNNING.md](RUNNING.md) for how to start/stop the backend, Celery
worker/beat, and frontend in this dev environment (native processes, no Docker CLI
available here).

## Documentation index

### Backend (`backend/app`)

| Module | Doc | Purpose |
|---|---|---|
| api | [docs/backend/api.md](backend/api.md) | HTTP surface — one router per feature |
| auth | [docs/backend/auth.md](backend/auth.md) | JWT auth, Entra ID SSO, delegated cloud-auth token handling |
| collectors | [docs/backend/collectors.md](backend/collectors.md) | NAVIXA Discover — per-cloud inventory collection |
| config | [docs/backend/config.md](backend/config.md) | Settings, secrets, rate limits |
| database | [docs/backend/database.md](backend/database.md) | SQLAlchemy base/session, seed scripts |
| models | [docs/backend/models.md](backend/models.md) | SQLAlchemy ORM models |
| schemas | [docs/backend/schemas.md](backend/schemas.md) | Pydantic request/response schemas |
| graph_engine | [docs/backend/graph_engine.md](backend/graph_engine.md) | NAVIXA Graph — Neo4j topology storage |
| hub_spoke_validator | [docs/backend/hub_spoke_validator.md](backend/hub_spoke_validator.md) | NAVIXA Validate — compliance rule engine |
| internet_path_engine | [docs/backend/internet_path_engine.md](backend/internet_path_engine.md) | NAVIXA Pathfinder — internet exposure analysis |
| ai_engine | [docs/backend/ai_engine.md](backend/ai_engine.md) | NAVIXA InsightAI — provider-agnostic LLM insights |
| reports | [docs/backend/reports.md](backend/reports.md) | PDF/Excel/HTML report generation |
| tenant_registry | [docs/backend/tenant_registry.md](backend/tenant_registry.md) | Cloud tenant/scope registry and sync |
| watch | [docs/backend/watch.md](backend/watch.md) | NAVIXA Watch — scheduled discovery and change detection |
| workers | [docs/backend/workers.md](backend/workers.md) | Celery task orchestration |

Entrypoint: `backend/app/main.py` (`create_app()`), mounted API prefix `/api/v1`. Migrations in `backend/alembic/`.

### Frontend (`frontend/src`)

| Module | Doc | Purpose |
|---|---|---|
| api | [docs/frontend/api.md](frontend/api.md) | Axios client + one module per backend domain |
| auth | [docs/frontend/auth.md](frontend/auth.md) | Auth/environment React Context, route guards |
| components | [docs/frontend/components.md](frontend/components.md) | Shared UI shell |
| pages | [docs/frontend/pages.md](frontend/pages.md) | Route-level page components |
| theme | [docs/frontend/theme.md](frontend/theme.md) | MUI theme definition |

Entrypoint: `frontend/src/main.tsx` → `App.tsx` (routing tree).
