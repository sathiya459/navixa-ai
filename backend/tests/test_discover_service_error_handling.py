"""Verifies run_discovery_for_scope never lets an unexpected exception
propagate out uncaught. tasks.py runs every scope under
`asyncio.gather(..., return_exceptions=True)` - if an exception escapes
here, it is silently discarded there: the scope stays "running" forever
with zero status rows and no visible error anywhere, which is exactly
what a stalled/misconfigured AWS credential call used to produce."""

import asyncio
import uuid

import pytest

from app.collectors import discover_service
from app.models.audit_job import AuditJobScope


class _FakeSession:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        pass


def test_unexpected_exception_marks_scope_failed_instead_of_propagating(monkeypatch):
    async def _boom(*_args, **_kwargs):
        raise RuntimeError("AccessDeniedException: not authorized to perform sso:GetRoleCredentials")

    monkeypatch.setattr(discover_service, "_discover_by_provider", _boom)

    db = _FakeSession()
    scope = AuditJobScope(id=uuid.uuid4(), audit_job_id=uuid.uuid4(), cloud_scope_id=uuid.uuid4())
    tenant = discover_service.CloudTenant(
        id=uuid.uuid4(), provider="aws", environment="dev", tenant_name="t", external_tenant_id="x"
    )

    # Must not raise.
    asyncio.run(
        discover_service.run_discovery_for_scope(db, scope, tenant, "111122223333", "us-east-1")
    )

    assert scope.status == "failed"
    assert scope.completed_at is not None
    error_rows = [row for row in db.added if getattr(row, "error_detail", None)]
    assert any("AccessDeniedException" in row.error_detail for row in error_rows)
