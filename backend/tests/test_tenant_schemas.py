from app.schemas.tenant import ScopeCreate, TenantCreate


def test_tenant_create_accepts_valid_provider():
    tenant = TenantCreate(provider="aws", tenant_name="Acme Corp", external_tenant_id="o-1234")
    assert tenant.provider == "aws"


def test_scope_create_accepts_valid_scope_type():
    scope = ScopeCreate(scope_type="account", external_scope_id="111122223333", display_name="Prod")
    assert scope.scope_type == "account"


def test_tenant_create_defaults_to_delegated_auth_mode():
    tenant = TenantCreate(provider="azure", tenant_name="Acme Corp", external_tenant_id="tenant-1")
    assert tenant.auth_mode == "delegated"


def test_tenant_create_accepts_app_only_with_registration_metadata():
    tenant = TenantCreate(
        provider="azure",
        tenant_name="Acme Corp",
        external_tenant_id="tenant-1",
        auth_mode="app_only",
        app_registration_client_id="client-1",
        app_registration_tenant_id="tenant-1",
        app_registration_redirect_uri="http://localhost:8000/callback",
    )
    assert tenant.auth_mode == "app_only"
    assert tenant.app_registration_client_id == "client-1"
