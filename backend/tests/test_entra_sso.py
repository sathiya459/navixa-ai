from fastapi.testclient import TestClient

from app.auth.entra import is_entra_configured
from app.auth.sso_service import get_or_create_entra_user
from app.main import app


def test_entra_not_configured_by_default(monkeypatch):
    # Pin explicitly: a developer's local .env with a real Entra App
    # Registration configured (as this project's does, post Section 8a
    # setup) would otherwise leak into this test via the shared settings
    # singleton.
    from app.auth import entra

    monkeypatch.setattr(entra.settings, "entra_tenant_id", None)
    monkeypatch.setattr(entra.settings, "entra_client_id", None)
    monkeypatch.setattr(entra.settings, "entra_client_secret", None)
    assert is_entra_configured() is False


def test_sso_login_returns_503_when_not_configured(monkeypatch):
    from app.api.v1 import auth as auth_router_module

    monkeypatch.setattr(auth_router_module.settings, "entra_tenant_id", None)
    monkeypatch.setattr(auth_router_module.settings, "entra_client_id", None)
    monkeypatch.setattr(auth_router_module.settings, "entra_client_secret", None)

    client = TestClient(app)
    response = client.get("/api/v1/auth/sso/entra/login", follow_redirects=False)
    assert response.status_code == 503


def test_sso_callback_redirects_to_frontend_with_error_when_not_configured(monkeypatch):
    """The callback is a full-page browser navigation landed on by Entra's
    own redirect, not an API call a frontend can inspect a status code
    from - so failures redirect back into the SPA with an error fragment
    rather than raising, which would just show the browser a bare error
    page with nothing the SPA can react to."""
    from app.api.v1 import auth as auth_router_module

    monkeypatch.setattr(auth_router_module.settings, "entra_tenant_id", None)
    monkeypatch.setattr(auth_router_module.settings, "entra_client_id", None)
    monkeypatch.setattr(auth_router_module.settings, "entra_client_secret", None)

    client = TestClient(app)
    response = client.get(
        "/api/v1/auth/sso/entra/callback", params={"code": "fake-code"}, follow_redirects=False
    )
    assert response.status_code in (302, 307)
    assert "error=sso_not_configured" in response.headers["location"]


def test_get_authorization_url_when_configured(monkeypatch):
    """msal.ConfidentialClientApplication performs a live network call to
    Microsoft's OIDC discovery endpoint at construction time - even with a
    fake tenant ID, so it genuinely cannot be unit-tested without network
    reachability to Microsoft's endpoints. This mocks the MSAL client
    itself to verify our URL-building call, not MSAL's own behavior."""
    from app.auth import entra

    monkeypatch.setattr(entra.settings, "entra_tenant_id", "tenant-1")
    monkeypatch.setattr(entra.settings, "entra_client_id", "client-1")
    monkeypatch.setattr(entra.settings, "entra_client_secret", "secret-1")
    assert entra.is_entra_configured() is True

    class _FakeMsalApp:
        def get_authorization_request_url(self, scopes, state, redirect_uri):
            return f"https://login.microsoftonline.com/tenant-1/authorize?state={state}"

    monkeypatch.setattr(entra, "_get_msal_app", lambda: _FakeMsalApp())

    url = entra.get_authorization_url("state-123")
    assert "login.microsoftonline.com" in url
    assert "state-123" in url


class _FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


class _FakeDB:
    """Minimal stand-in for a SQLAlchemy Session, just enough to exercise
    get_or_create_entra_user's control flow without a real database."""

    def __init__(self):
        self.added = []
        self.committed = False

    def query(self, model):
        from app.models.role import Role

        if model is Role:
            return _FakeQuery(Role(name="viewer"))
        return _FakeQuery(None)  # no existing user

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        import uuid

        for obj in self.added:
            if not getattr(obj, "id", None):
                obj.id = uuid.uuid4()

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        pass


def test_get_or_create_entra_user_provisions_new_user_with_viewer_role():
    db = _FakeDB()
    claims = {"oid": "entra-oid-1", "preferred_username": "alice@example.com", "name": "Alice"}

    user = get_or_create_entra_user(db, claims)

    assert user.email == "alice@example.com"
    assert user.auth_provider == "entra_id"
    assert user.external_id == "entra-oid-1"
    assert db.committed is True
    assert any(type(obj).__name__ == "UserRole" for obj in db.added)
