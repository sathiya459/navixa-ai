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

    # Neo4j (navixa_graph) - wired in Phase 3. Named multi-database support
    # (i.e. an actual database literally called "navixa_graph") is a Neo4j
    # Enterprise-only feature; Community Edition only has the single
    # default database. Defaulting to "neo4j" here so this works out of
    # the box on Community; set NEO4J_DATABASE=navixa_graph if running
    # against Enterprise with that database created.
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "changeme"
    neo4j_database: str = "neo4j"

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
    # Where the browser lands after a successful SSO callback, with tokens
    # appended as a URL fragment (never a query string, so they aren't
    # captured in server access logs or Referer headers along the way).
    frontend_sso_redirect_url: str = "http://localhost:5173/sso/callback"

    # Cloud auth mode for NAVIXA Discover (Section 8a): "delegated" uses
    # whatever identity the developer already signed into on this machine
    # via each cloud's own CLI (`az login`, `aws sso login`,
    # `gcloud auth application-default login`, `oci session authenticate`)
    # - the SDK default credential chain picks that up automatically, no
    # separate flow needed in this backend. "app_only" uses the Phase 5
    # federation paths below (AssumeRole / ClientSecretCredential /
    # impersonated service account / OCI session signer). Falls back to
    # Phase 1/2's stub credentials when the selected mode isn't configured,
    # so local dev without either keeps working unchanged.
    cloud_auth_mode: str = "app_only"

    # Named profile for delegated AWS auth (e.g. one set up via
    # `aws sso login --sso-session ...`). boto3/aioboto3 only pick up
    # AWS_PROFILE from the real OS environment, not from this app's .env
    # file (pydantic-settings doesn't export values into os.environ) - so
    # this is passed explicitly to aioboto3.Session(profile_name=...)
    # instead of relying on ambient environment propagation.
    aws_profile: str | None = None

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
    # principal auth for workloads already running on OCI compute. This
    # session-token path (from `oci session authenticate`) already *is*
    # delegated user auth, so OCI doesn't need a separate delegated branch.
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


# Fields that may hold real secrets, mapped to the name they're stored
# under in a Secret Manager/Key Vault when secret_provider != "env". Only
# fields actually present in the vault get overridden - a secret that
# doesn't exist there yet just keeps its env/.env/default value, so this
# stays forward-compatible as more secrets are migrated over time.
_SECRET_FIELD_MAP: dict[str, str] = {
    "jwt_secret_key": "navixa-jwt-secret-key",
    "database_url": "navixa-database-url",
    "neo4j_password": "navixa-neo4j-password",
    "entra_client_secret": "navixa-entra-client-secret",
    "anthropic_api_key": "navixa-anthropic-api-key",
    "openai_api_key": "navixa-openai-api-key",
    "azure_openai_api_key": "navixa-azure-openai-api-key",
    "gemini_api_key": "navixa-gemini-api-key",
    "azure_federation_client_secret": "navixa-azure-federation-client-secret",
    "aws_audit_external_id": "navixa-aws-audit-external-id",
}


def _apply_secret_overrides(settings: Settings) -> None:
    if settings.secret_provider == "env":
        return

    # Local import + direct provider construction (not get_secret_provider(),
    # which calls get_settings() itself) - calling back into get_settings()
    # from here, before this call has returned and been cached by
    # @lru_cache, would recurse infinitely.
    from app.config.secrets import SecretProviderError, build_secret_provider

    provider = build_secret_provider(
        settings.secret_provider,
        azure_key_vault_url=settings.azure_key_vault_url,
        aws_region=settings.aws_secrets_manager_region,
    )

    for field_name, secret_name in _SECRET_FIELD_MAP.items():
        try:
            setattr(settings, field_name, provider.get_secret(secret_name))
        except SecretProviderError:
            continue


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    _apply_secret_overrides(settings)
    return settings
