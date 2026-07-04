import asyncio
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from app.tenant_registry import aws_import


def _fake_connection() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), environment="dev", provider="aws", name="prod-sso")


class _FakeTenant:
    def __init__(self, id, connection_id, external_tenant_id: str = ""):
        self.id = id
        self.connection_id = connection_id
        self.external_tenant_id = external_tenant_id


class _FakeScope:
    def __init__(self, external_scope_id: str):
        self.external_scope_id = external_scope_id


def test_discover_available_tenants_with_no_existing_tenant_marks_nothing_added(monkeypatch):
    connection = _fake_connection()

    async def fake_list_sso_accounts(conn):
        return [("111111111111", "Account One"), ("222222222222", "Account Two")]

    monkeypatch.setattr(aws_import, "list_sso_accounts", fake_list_sso_accounts)
    monkeypatch.setattr(aws_import, "list_tenants", lambda db, provider, environment: [])

    result = asyncio.run(aws_import.discover_available_tenants(connection, db=None, environment="dev"))

    assert {t.tenant_id for t in result} == {"111111111111", "222222222222"}
    assert all(t.already_added is False for t in result)


def test_discover_available_tenants_marks_scopes_already_added_under_this_connections_tenant(
    monkeypatch,
):
    connection = _fake_connection()
    tenant = _FakeTenant(id=uuid.uuid4(), connection_id=connection.id)

    async def fake_list_sso_accounts(conn):
        return [("111111111111", "Account One"), ("222222222222", "Account Two")]

    monkeypatch.setattr(aws_import, "list_sso_accounts", fake_list_sso_accounts)
    monkeypatch.setattr(aws_import, "list_tenants", lambda db, provider, environment: [tenant])
    monkeypatch.setattr(
        aws_import, "list_scopes", lambda db, tenant_id: [_FakeScope("111111111111")]
    )

    result = asyncio.run(aws_import.discover_available_tenants(connection, db=None, environment="dev"))

    by_id = {t.tenant_id: t for t in result}
    assert by_id["111111111111"].already_added is True
    assert by_id["222222222222"].already_added is False


def test_import_tenants_creates_exactly_one_tenant_for_multiple_accounts(monkeypatch):
    connection = _fake_connection()
    created_tenants = []
    created_scopes = []

    async def fake_list_sso_accounts(conn):
        return [("111111111111", "Account One"), ("222222222222", "Account Two")]

    def fake_create_tenant(db, payload, created_by):
        tenant = _FakeTenant(id=uuid.uuid4(), connection_id=connection.id, external_tenant_id=payload.external_tenant_id)
        created_tenants.append(tenant)
        return tenant

    def fake_create_scope(db, tenant_id, payload):
        created_scopes.append((tenant_id, payload.external_scope_id, payload.scope_type))

    monkeypatch.setattr(aws_import, "list_sso_accounts", fake_list_sso_accounts)
    monkeypatch.setattr(aws_import, "list_tenants", lambda db, provider, environment: [])
    monkeypatch.setattr(aws_import, "list_scopes", lambda db, tenant_id: [])
    monkeypatch.setattr(aws_import, "create_tenant", fake_create_tenant)
    monkeypatch.setattr(aws_import, "create_scope", fake_create_scope)

    result = asyncio.run(
        aws_import.import_tenants(
            connection,
            db=None,
            environment="dev",
            tenant_ids=["111111111111", "222222222222"],
            created_by=uuid.uuid4(),
        )
    )

    # Exactly one tenant, regardless of how many accounts were imported.
    assert len(result) == 1
    assert len(created_tenants) == 1
    assert created_scopes == [
        (result[0].id, "111111111111", "account"),
        (result[0].id, "222222222222", "account"),
    ]


def test_import_tenants_reuses_existing_tenant_and_skips_already_added_and_unknown_ids(monkeypatch):
    connection = _fake_connection()
    tenant = _FakeTenant(id=uuid.uuid4(), connection_id=connection.id)
    created_tenants = []
    created_scopes = []

    async def fake_list_sso_accounts(conn):
        return [("111111111111", "Account One"), ("222222222222", "Account Two")]

    def fake_create_tenant(db, payload, created_by):
        created_tenants.append(payload)
        raise AssertionError("should not create a new tenant when one already exists")

    def fake_create_scope(db, tenant_id, payload):
        created_scopes.append((tenant_id, payload.external_scope_id))

    monkeypatch.setattr(aws_import, "list_sso_accounts", fake_list_sso_accounts)
    monkeypatch.setattr(aws_import, "list_tenants", lambda db, provider, environment: [tenant])
    monkeypatch.setattr(
        aws_import, "list_scopes", lambda db, tenant_id: [_FakeScope("111111111111")]
    )
    monkeypatch.setattr(aws_import, "create_tenant", fake_create_tenant)
    monkeypatch.setattr(aws_import, "create_scope", fake_create_scope)

    result = asyncio.run(
        aws_import.import_tenants(
            connection,
            db=None,
            environment="dev",
            tenant_ids=["111111111111", "222222222222", "account-does-not-exist"],
            created_by=uuid.uuid4(),
        )
    )

    assert result == [tenant]
    assert created_tenants == []
    assert created_scopes == [(tenant.id, "222222222222")]


def test_import_tenants_recovers_from_concurrent_tenant_creation_race(monkeypatch):
    """Regression test: two near-simultaneous imports for the same
    connection (e.g. a fast double-click) can both see no existing tenant
    and both call create_tenant - this happened in practice, producing two
    duplicate tenants for one connection. The DB's partial unique index
    (migration c3d4e5f6a7b8) now rejects the loser with IntegrityError;
    this call must recover by rolling back and reusing the winning tenant
    rather than erroring out or creating a second tenant."""
    connection = _fake_connection()
    winning_tenant = _FakeTenant(id=uuid.uuid4(), connection_id=connection.id)
    rollback_calls = []
    created_scopes = []

    async def fake_list_sso_accounts(conn):
        return [("111111111111", "Account One")]

    # First lookup (before the "other request" committed) finds nothing;
    # the lookup after recovering from the IntegrityError finds the tenant
    # the other request created.
    lookup_results = iter([[], [winning_tenant]])
    monkeypatch.setattr(
        aws_import, "list_tenants", lambda db, provider, environment: next(lookup_results)
    )

    def fake_create_tenant(db, payload, created_by):
        raise IntegrityError("INSERT", {}, Exception("duplicate key"))

    def fake_rollback():
        rollback_calls.append(True)

    def fake_create_scope(db, tenant_id, payload):
        created_scopes.append((tenant_id, payload.external_scope_id))

    monkeypatch.setattr(aws_import, "list_sso_accounts", fake_list_sso_accounts)
    monkeypatch.setattr(aws_import, "list_scopes", lambda db, tenant_id: [])
    monkeypatch.setattr(aws_import, "create_tenant", fake_create_tenant)
    monkeypatch.setattr(aws_import, "create_scope", fake_create_scope)

    fake_db = SimpleNamespace(rollback=fake_rollback)

    result = asyncio.run(
        aws_import.import_tenants(
            connection,
            db=fake_db,
            environment="dev",
            tenant_ids=["111111111111"],
            created_by=uuid.uuid4(),
        )
    )

    assert result == [winning_tenant]
    assert rollback_calls == [True]
    assert created_scopes == [(winning_tenant.id, "111111111111")]


def test_import_tenants_reraises_integrity_error_if_recovery_lookup_also_finds_nothing(
    monkeypatch,
):
    """If the IntegrityError wasn't actually caused by the expected race
    (recovery lookup still finds no tenant), re-raise rather than silently
    swallowing an unrelated constraint violation."""
    connection = _fake_connection()

    async def fake_list_sso_accounts(conn):
        return [("111111111111", "Account One")]

    monkeypatch.setattr(aws_import, "list_sso_accounts", fake_list_sso_accounts)
    monkeypatch.setattr(aws_import, "list_tenants", lambda db, provider, environment: [])

    def fake_create_tenant(db, payload, created_by):
        raise IntegrityError("INSERT", {}, Exception("some other constraint"))

    monkeypatch.setattr(aws_import, "create_tenant", fake_create_tenant)
    fake_db = SimpleNamespace(rollback=lambda: None)

    with pytest.raises(IntegrityError):
        asyncio.run(
            aws_import.import_tenants(
                connection,
                db=fake_db,
                environment="dev",
                tenant_ids=["111111111111"],
                created_by=uuid.uuid4(),
            )
        )
