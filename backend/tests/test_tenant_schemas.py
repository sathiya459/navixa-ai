from app.schemas.tenant import ScopeCreate, TenantCreate


def test_tenant_create_accepts_valid_provider():
    tenant = TenantCreate(provider="aws", tenant_name="Acme Corp", external_tenant_id="o-1234")
    assert tenant.provider == "aws"


def test_scope_create_accepts_valid_scope_type():
    scope = ScopeCreate(scope_type="account", external_scope_id="111122223333", display_name="Prod")
    assert scope.scope_type == "account"
