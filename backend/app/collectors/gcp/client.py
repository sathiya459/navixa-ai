"""GCP credential broker for NAVIXA Discover (Section 8 / 8a).

Two real modes, selected by `settings.cloud_auth_mode`:
- "delegated": google.auth.default(), which picks up whatever the
  developer already signed into via
  `gcloud auth application-default login` on this machine - no separate
  flow needed in this backend.
- "app_only": the platform's own default application credentials
  impersonate a fixed audit service account (`gcp_audit_service_account`)
  that has been granted read access on target projects. True Workforce
  Identity Federation is a full OIDC token exchange against GCP's STS
  endpoint using an external IdP-issued token; this implements the more
  common simplified equivalent instead - a deliberate scope reduction,
  documented here rather than silently passed off as full WIF.

Falls back to the Phase 2 stub when the selected mode isn't configured,
so local dev without GCP credentials keeps working.
"""

from google.auth import default as google_auth_default
from google.auth.credentials import AnonymousCredentials, Credentials
from google.auth.impersonated_credentials import Credentials as ImpersonatedCredentials

from app.config.settings import get_settings

settings = get_settings()

_IMPERSONATION_SCOPES = ["https://www.googleapis.com/auth/cloud-platform.read-only"]


def is_gcp_federation_configured() -> bool:
    return bool(settings.gcp_audit_service_account)


async def get_scoped_credential(external_scope_id: str) -> Credentials:
    if settings.cloud_auth_mode == "delegated":
        credentials, _ = google_auth_default()
        return credentials

    if not is_gcp_federation_configured():
        return AnonymousCredentials()

    source_credentials, _ = google_auth_default()
    return ImpersonatedCredentials(
        source_credentials=source_credentials,
        target_principal=settings.gcp_audit_service_account,
        target_scopes=_IMPERSONATION_SCOPES,
        lifetime=900,
    )
