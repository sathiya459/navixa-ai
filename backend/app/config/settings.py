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

    # NAVIXA Reports (Section 17) - local filesystem for dev; swap for
    # object storage (S3/Blob/GCS) in production via this same setting.
    reports_dir: str = "generated_reports"

    # Entra ID SSO/OIDC (Section 6, Phase 5). MFA is enforced at the IdP via
    # Entra Conditional Access policies, not application code - there is no
    # in-app MFA step to implement. Unset means local JWT auth stays the
    # only login path (dev default per Section 6).
    entra_tenant_id: str | None = None
    entra_client_id: str | None = None
    entra_client_secret: str | None = None
    entra_redirect_uri: str = "http://localhost:8000/api/v1/auth/sso/entra/callback"

    # Cloud federation for NAVIXA Discover (Section 8, Phase 5). Each
    # provider falls back to Phase 1/2's stub credentials when its
    # federation config is unset, so local dev without real cloud accounts
    # keeps working unchanged.
    aws_audit_role_name: str = "NavixaAuditRole"
    aws_audit_external_id: str | None = None

    azure_federation_tenant_id: str | None = None
    azure_federation_client_id: str | None = None
    azure_federation_client_secret: str | None = None

    # GCP Workforce Identity Federation is normally a full OIDC token
    # exchange against GCP's STS endpoint; this implements the common
    # simplified equivalent - impersonating a fixed audit service account
    # per project - and documents that as a deliberate scope reduction,
    # not a misunderstanding of WIF.
    gcp_audit_service_account: str | None = None

    # OCI Federation / Identity Domains: a session-token-based signer path
    # (federated) when a session token is available, else instance
    # principal auth for workloads already running on OCI compute.
    oci_session_token_path: str | None = None
    oci_config_profile: str = "DEFAULT"

    # Secret Manager (Section 7, Phase 5). "env" (default) reads secrets
    # from environment variables / .env, matching Section 7's development
    # posture. Production deployments set this to "aws_secrets_manager" or
    # "azure_key_vault" instead of putting real secrets in env files.
    secret_provider: str = "env"
    aws_secrets_manager_region: str = "us-east-1"
    azure_key_vault_url: str | None = None

    # Celery worker scaling (Section 20 Phase 5 "Scaling"). Concurrency is
    # per-worker-process; horizontal scale-out is achieved by running more
    # worker containers/replicas (see docker-compose.yml comments), not by
    # raising this alone.
    celery_worker_concurrency: int = 4


@lru_cache
def get_settings() -> Settings:
    return Settings()
