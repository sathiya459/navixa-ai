"""GCP credential broker for NAVIXA Discover (Section 8).

True Workforce Identity Federation is a full OIDC token exchange against
GCP's STS endpoint using an external IdP-issued token. This implements the
more common simplified equivalent instead: the platform's own default
application credentials impersonate a fixed audit service account
(`gcp_audit_service_account`) that has been granted read access on target
projects - a deliberate scope reduction, documented here rather than
silently passed off as full WIF. Falls back to the Phase 2 stub when
unconfigured, so local dev without GCP credentials keeps working.
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
    if not is_gcp_federation_configured():
        return AnonymousCredentials()

    source_credentials, _ = google_auth_default()
    return ImpersonatedCredentials(
        source_credentials=source_credentials,
        target_principal=settings.gcp_audit_service_account,
        target_scopes=_IMPERSONATION_SCOPES,
        lifetime=900,
    )
