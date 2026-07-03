import asyncio
import uuid
from types import SimpleNamespace

from app.tenant_registry import azure_import


def _fake_connection() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), environment="dev", provider="azure")


class _FakeTenant:
    def __init__(self, external_tenant_id: str):
        self.external_tenant_id = external_tenant_id


def test_discover_available_tenants_marks_already_added(monkeypatch):
    connection = _fake_connection()

    async def fake_list_available_tenants(conn):
        return [
            {"tenant_id": "tenant-1", "display_name": "Tenant One"},
            {"tenant_id": "tenant-2", "display_name": "Tenant Two"},
        ]

    monkeypatch.setattr(azure_import, "list_available_tenants", fake_list_available_tenants)
    monkeypatch.setattr(
        azure_import, "list_tenants", lambda db, provider, environment: [_FakeTenant("tenant-1")]
    )

    result = asyncio.run(azure_import.discover_available_tenants(connection, db=None, environment="dev"))

    by_id = {t.tenant_id: t for t in result}
    assert by_id["tenant-1"].already_added is True
    assert by_id["tenant-2"].already_added is False


def test_import_tenants_skips_already_added_and_unknown_ids(monkeypatch):
    connection = _fake_connection()
    created_tenants = []
    created_scopes = []

    async def fake_list_available_tenants(conn):
        return [{"tenant_id": "tenant-2", "display_name": "Tenant Two"}]

    async def fake_list_subscriptions_for_tenant(conn, tenant_id):
        return [{"subscription_id": "sub-1", "display_name": "Prod Subscription"}]

    def fake_create_tenant(db, payload, created_by):
        tenant = SimpleNamespace(id=uuid.uuid4(), external_tenant_id=payload.external_tenant_id)
        created_tenants.append(tenant)
        return tenant

    def fake_create_scope(db, tenant_id, payload):
        created_scopes.append((tenant_id, payload.external_scope_id))

    monkeypatch.setattr(azure_import, "list_available_tenants", fake_list_available_tenants)
    monkeypatch.setattr(azure_import, "list_subscriptions_for_tenant", fake_list_subscriptions_for_tenant)
    monkeypatch.setattr(
        azure_import, "list_tenants", lambda db, provider, environment: [_FakeTenant("tenant-1")]
    )
    monkeypatch.setattr(azure_import, "create_tenant", fake_create_tenant)
    monkeypatch.setattr(azure_import, "create_scope", fake_create_scope)

    result = asyncio.run(
        azure_import.import_tenants(
            connection,
            db=None,
            environment="dev",
            tenant_ids=["tenant-1", "tenant-2", "tenant-does-not-exist"],
            created_by=uuid.uuid4(),
        )
    )

    assert len(result) == 1
    assert result[0].external_tenant_id == "tenant-2"
    assert created_scopes == [(result[0].id, "sub-1")]
