# database

SQLAlchemy setup and one-off bootstrap scripts.

## Files

- `base.py` — SQLAlchemy `Base` with UUID primary-key/timestamp conventions shared by all models.
- `session.py` — engine, `SessionLocal`, and the `get_db` FastAPI dependency.
- `seed_admin.py` — CLI script to bootstrap the initial admin user.
- `seed_roles.py` — CLI script to bootstrap RBAC roles.

## Notes

Schema changes go through Alembic migrations in `backend/alembic/versions/` (8 migrations as of this writing: initial schema, environments/connections, delegated token cache, roles collapse to admin/reader, AI insights/reports/scheduled discovery, AI analysis finding module, audit-job resource types, cloud tenant auth mode).
