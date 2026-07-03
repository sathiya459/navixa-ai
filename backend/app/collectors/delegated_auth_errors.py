def build_delegated_auth_detail(environment: str, provider: str) -> dict:
    """Structured 409 body any endpoint can return when an environment has
    no valid cached SSO session.

    AWS's popup+callback flow can be retried transparently: the frontend's
    axios interceptor (frontend/src/api/client.ts) recognizes `code`,
    fetches `start_url` (a GET returning {authorize_url}), opens it in a
    popup, and retries the original request on success.

    Azure's delegated auth is a device-code flow instead (see
    app/collectors/azure/client.py's docstring for why) - it requires
    showing the admin a code, which can't be done transparently from an
    arbitrary failed request. For `provider == "azure"`, `start_url` is
    omitted; the frontend must surface `message` and point the admin at
    the Connections page instead of attempting a popup.
    """
    detail = {
        "code": "delegated_auth_required",
        "environment": environment,
        "provider": provider,
        "message": f"Sign in via SSO to connect the {environment} environment's {provider.upper()} account.",
    }
    if provider != "azure":
        detail["start_url"] = f"/connections/{environment}/{provider}/delegated-auth/start"
    else:
        detail["message"] = (
            f"Connect the {environment} environment's Azure account from the Connections page "
            "first (Azure sign-in requires a device code, shown there)."
        )
    return detail


class DelegatedAuthRequiredError(Exception):
    """Raised when an (environment, provider) EnvironmentConnection has no
    valid cached SSO session (never connected, or refresh failed) - the
    caller must complete the SSO popup login (once per environment, not
    per tenant) before cloud data can be fetched. Carries enough to build
    the popup's start URL."""

    def __init__(self, environment: str, provider: str):
        self.environment = environment
        self.provider = provider
        super().__init__(f"Delegated SSO session required for {environment}/{provider}")
