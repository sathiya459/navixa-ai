def build_delegated_auth_detail(tenant_id: str, provider: str) -> dict:
    """Structured 409 body any endpoint can return when a tenant has no
    valid cached SSO session - the frontend's axios interceptor
    (frontend/src/api/client.ts) recognizes `code` and opens the matching
    popup automatically, from any API call, not just one button.

    `start_url` is relative to the API's own base URL (VITE_API_BASE_URL,
    e.g. "http://localhost:8000/api/v1") rather than the site root, since
    the delegated-auth routes are mounted under that same prefix
    (app/main.py: `api_router` at `settings.api_v1_prefix`).
    """
    return {
        "code": "delegated_auth_required",
        "start_url": f"/tenants/{tenant_id}/delegated-auth/{provider}/start",
        "message": f"Sign in to this tenant's {provider.upper()} account via SSO to continue.",
    }


class DelegatedAuthRequiredError(Exception):
    """Raised when a CloudTenant in delegated mode has no valid cached SSO
    session (never connected, or refresh failed) - the caller must
    complete the per-tenant SSO popup login before cloud data can be
    fetched. Carries enough to build the popup's start URL."""

    def __init__(self, tenant_id: str, provider: str):
        self.tenant_id = tenant_id
        self.provider = provider
        super().__init__(f"Delegated SSO session required for tenant {tenant_id} ({provider})")
