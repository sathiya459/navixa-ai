# config

Application settings, secrets abstraction, and rate limiting.

## Files

- `settings.py` — pydantic-settings `Settings` class: DB/Redis/Neo4j URLs, JWT config, CORS origins, AI provider keys (Claude/OpenAI/Azure OpenAI/Gemini).
- `secrets.py` — abstracts a Secret Manager/Key Vault in production; falls back to env vars in dev.
- `rate_limits.py` — per-provider/per-resource-type max-concurrency limits for Discover collectors.
