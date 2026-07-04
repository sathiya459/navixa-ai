"""Verifies NAVIXA Discover reports progress incrementally - each resource
type's on_result callback fires as soon as that type finishes, not only
after every type in the scope has completed - and that a stalled
credential/session setup call times out instead of hanging the scope
forever."""

import asyncio

import pytest

from app.collectors.aws import orchestrator as aws_orchestrator
from app.collectors.base import CollectionResult, run_collectors_with_progress


async def _slow_success(resource_type: str, delay: float) -> CollectionResult:
    await asyncio.sleep(delay)
    return CollectionResult(resource_type=resource_type, status="success", items=[{"id": "1"}])


async def _immediate_failure(resource_type: str) -> CollectionResult:
    raise RuntimeError("boom")


def test_on_result_fires_per_completed_type_not_in_bulk():
    seen_order: list[str] = []

    async def on_result(result: CollectionResult) -> None:
        seen_order.append(result.resource_type)

    async def run():
        return await run_collectors_with_progress(
            {
                "slow": _slow_success("slow", 0.05),
                "fast": _slow_success("fast", 0.0),
            },
            on_result=on_result,
        )

    results = asyncio.run(run())

    assert seen_order == ["fast", "slow"]
    assert {r.resource_type for r in results} == {"slow", "fast"}


def test_run_collectors_with_progress_reports_failure_with_correct_resource_type():
    reported: list[CollectionResult] = []

    async def on_result(result: CollectionResult) -> None:
        reported.append(result)

    async def run():
        return await run_collectors_with_progress(
            {"security_group": _immediate_failure("security_group")}, on_result=on_result
        )

    results = asyncio.run(run())

    assert results[0].resource_type == "security_group"
    assert results[0].status == "failed"
    assert reported[0].resource_type == "security_group"


def test_credential_setup_timeout_reports_failure_instead_of_hanging(monkeypatch):
    async def hangs_forever(*_args, **_kwargs):
        await asyncio.sleep(10)

    monkeypatch.setattr(aws_orchestrator, "assume_role_for_scope", hangs_forever)
    monkeypatch.setattr(aws_orchestrator, "CREDENTIAL_SETUP_TIMEOUT_SECONDS", 0.05)

    results = asyncio.run(
        aws_orchestrator.discover_aws_scope(None, "111122223333", "us-east-1")
    )

    assert len(results) == 1
    assert results[0].resource_type == "_credentials"
    assert results[0].status == "failed"


def test_credential_setup_non_timeout_error_reports_failure_instead_of_propagating(monkeypatch):
    """Regression test: a non-timeout exception from credential setup (e.g.
    a real AccessDenied from sso.get_role_credentials, often caused by
    settings.aws_audit_role_name not matching the permission set actually
    granted) used to propagate all the way out of discover_aws_scope
    uncaught, since only TimeoutError was handled here. tasks.py's
    top-level gather(return_exceptions=True) then silently discarded it,
    leaving the scope "running" forever with zero VPCs and no error."""

    async def raises_access_denied(*_args, **_kwargs):
        raise RuntimeError("AccessDeniedException: User is not authorized to perform: sso:GetRoleCredentials")

    monkeypatch.setattr(aws_orchestrator, "assume_role_for_scope", raises_access_denied)

    results = asyncio.run(
        aws_orchestrator.discover_aws_scope(None, "111122223333", "us-east-1")
    )

    assert len(results) == 1
    assert results[0].resource_type == "_credentials"
    assert results[0].status == "failed"
    assert "AccessDeniedException" in results[0].error_detail


def test_credential_setup_delegated_auth_required_still_propagates(monkeypatch):
    """DelegatedAuthRequiredError must NOT be swallowed here - it's handled
    one level up in discover_service._discover_by_provider, which turns it
    into the standard "reconnect on the Connections page" message."""
    from app.collectors.delegated_auth_errors import DelegatedAuthRequiredError

    async def raises_delegated_auth_required(*_args, **_kwargs):
        raise DelegatedAuthRequiredError("dev", "aws")

    monkeypatch.setattr(aws_orchestrator, "assume_role_for_scope", raises_delegated_auth_required)

    with pytest.raises(DelegatedAuthRequiredError):
        asyncio.run(aws_orchestrator.discover_aws_scope(None, "111122223333", "us-east-1"))


@pytest.mark.parametrize(
    "resource_types,expected",
    [
        (None, {"network", "subnet", "route_table", "security_group", "gateway", "peering_connection"}),
        (["security_group"], {"network", "security_group"}),
    ],
)
def test_aws_expected_resource_types(resource_types, expected):
    assert aws_orchestrator.expected_resource_types(resource_types) == expected


class _FakeEc2:
    def __init__(self, regions: list[str]):
        self._regions = regions

    async def describe_regions(self):
        return {"Regions": [{"RegionName": r} for r in self._regions]}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return None


class _FakeSession:
    def __init__(self, regions: list[str]):
        self._regions = regions

    def client(self, _service):
        return _FakeEc2(self._regions)


def test_discover_aws_scope_fans_out_across_enabled_regions(monkeypatch):
    regions = ["us-east-1", "ap-south-1"]
    call_count = 0

    async def fake_assume_role(*_args, **_kwargs):
        return object()

    def fake_get_async_session(_creds, _region):
        return _FakeSession(regions)

    async def fake_network_collector(_session, _semaphore):
        nonlocal call_count
        call_count += 1
        return CollectionResult(resource_type="network", status="success", items=[{"VpcId": "vpc-1"}])

    monkeypatch.setattr(aws_orchestrator, "assume_role_for_scope", fake_assume_role)
    monkeypatch.setattr(aws_orchestrator, "get_async_session", fake_get_async_session)
    monkeypatch.setattr(
        aws_orchestrator, "_COLLECTORS_BY_RESOURCE_TYPE", {"network": fake_network_collector}
    )

    results = asyncio.run(
        aws_orchestrator.discover_aws_scope(None, "111122223333", "us-east-1", resource_types=["network"])
    )

    assert len(results) == 1
    result = results[0]
    assert result.resource_type == "network"
    assert result.status == "success"
    # Called once per enabled region, one item per region, each tagged
    # with its source region.
    assert call_count == len(regions)
    assert len(result.items) == len(regions)
    assert {item["_navixa_region"] for item in result.items} == set(regions)


def test_collect_across_regions_reports_partial_when_one_region_times_out(monkeypatch):
    monkeypatch.setattr(aws_orchestrator, "AWS_COLLECTOR_CALL_TIMEOUT_SECONDS", 0.02)
    monkeypatch.setattr(aws_orchestrator, "get_async_session", lambda _creds, region: region)

    async def one_slow_one_fast(session, _semaphore):
        if session == "ap-south-1":
            await asyncio.sleep(10)
        return CollectionResult(resource_type="network", status="success", items=[{"VpcId": "vpc-1"}])

    result = asyncio.run(
        aws_orchestrator._collect_across_regions(
            "network",
            one_slow_one_fast,
            creds=None,
            regions=["us-east-1", "ap-south-1"],
            semaphore=asyncio.Semaphore(10),
        )
    )

    assert result.status == "partial"
    assert len(result.items) == 1
    assert result.items[0]["_navixa_region"] == "us-east-1"
    assert "ap-south-1" in result.error_detail
