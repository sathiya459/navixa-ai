def build_delegated_auth_detail(environment: str, provider: str) -> dict:
    """Structured 409 body any endpoint can return when a connection has no
    valid cached SSO session.

    Both AWS and Azure authenticate via the device-code flow (see
    app/api/v1/delegated_auth.py's module docstring for why) - it requires
    showing the admin a code, which can't be done transparently from an
    arbitrary failed request. The frontend must surface `message` and
    point the admin at the Connections page to complete sign-in there.
    """
    return {
        "code": "delegated_auth_required",
        "environment": environment,
        "provider": provider,
        "message": (
            f"Connect the {environment} environment's {provider.upper()} account from the "
            "Connections page first (sign-in requires a device code, shown there)."
        ),
    }


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
