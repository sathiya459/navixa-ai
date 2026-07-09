# config

Application settings, secrets abstraction, and rate limiting.

## Files

- `settings.py` — pydantic-settings `Settings` class: Postgres/Redis URLs, JWT config, CORS origins, AI provider keys (Claude/OpenAI/Azure OpenAI/Gemini). `.env` is loaded via an absolute path (`Path(__file__).resolve().parents[2] / ".env"`, i.e. `backend/.env`) rather than a bare relative `"env_file"`, so it resolves correctly no matter what working directory the process was launched from - a relative path would silently fail to load `.env` (every field falling back to its hardcoded class default, no error raised) whenever launched from outside `backend/`.
- `secrets.py` — abstracts a Secret Manager/Key Vault in production; falls back to env vars in dev.
- `rate_limits.py` — per-provider/per-resource-type max-concurrency limits for Discover collectors.
