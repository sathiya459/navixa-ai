from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "NAVIXA AI"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    # PostgreSQL (navixa_db)
    database_url: str = "postgresql+psycopg://navixa:navixa@localhost:5432/navixa_db"

    # Redis (navixa_cache)
    redis_url: str = "redis://localhost:6379/0"

    # Neo4j (navixa_graph) - wired in Phase 3
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "changeme"

    # JWT
    jwt_secret_key: str = "changeme-dev-only"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 7

    cors_origins: list[str] = ["http://localhost:3000"]

    # NAVIXA InsightAI providers (Section 15) - unset means "not configured";
    # never hardcode a real key here, only via environment/.env/Secret Manager.
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"

    azure_openai_api_key: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_deployment: str | None = None

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"

    aws_bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    aws_default_region: str = "us-east-1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
