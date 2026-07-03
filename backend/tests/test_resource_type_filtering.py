"""Verifies the New Job "Select Service/Resource Types" step actually
restricts which collectors run, rather than just filtering afterward -
mocks out credential resolution and the collector functions themselves so
no real cloud calls happen."""

import asyncio

import pytest

from app.collectors.aws import orchestrator as aws_orchestrator
from app.collectors.azure import orchestrator as azure_orchestrator
from app.collectors.base import CollectionResult


def _fake_collector(resource_type: str, calls: list[str]):
    async def _collect(*_args, **_kwargs):
        calls.append(resource_type)
        return CollectionResult(resource_type=resource_type, status="success")

    return _collect


@pytest.fixture(autouse=True)
def no_real_aws_calls(monkeypatch):
    async def fake_assume_role(*_args, **_kwargs):
        return None

    monkeypatch.setattr(aws_orchestrator, "assume_role_for_scope", fake_assume_role)
    monkeypatch.setattr(aws_orchestrator, "get_async_session", lambda *_a, **_k: object())


@pytest.fixture(autouse=True)
def no_real_azure_calls(monkeypatch):
    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc):
            return None

    monkeypatch.setattr(azure_orchestrator, "get_scoped_credential", lambda *_a, **_k: _FakeClient())
    monkeypatch.setattr(azure_orchestrator, "get_network_client", lambda *_a, **_k: _FakeClient())


def test_aws_discovery_only_runs_selected_collectors(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        aws_orchestrator,
        "_COLLECTORS_BY_RESOURCE_TYPE",
        {rt: _fake_collector(rt, calls) for rt in aws_orchestrator._COLLECTORS_BY_RESOURCE_TYPE},
    )

    asyncio.run(
        aws_orchestrator.discover_aws_scope(
            None, "111122223333", "us-east-1", resource_types=["security_group"]
        )
    )

    assert set(calls) == {"network", "security_group"}


def test_aws_discovery_collects_everything_when_unfiltered(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        aws_orchestrator,
        "_COLLECTORS_BY_RESOURCE_TYPE",
        {rt: _fake_collector(rt, calls) for rt in aws_orchestrator._COLLECTORS_BY_RESOURCE_TYPE},
    )

    asyncio.run(aws_orchestrator.discover_aws_scope(None, "111122223333", "us-east-1"))

    assert set(calls) == {"network", "subnet", "route_table", "security_group", "gateway", "peering_connection"}


def test_azure_discovery_only_runs_selected_collectors(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        azure_orchestrator,
        "_COLLECTORS_BY_RESOURCE_TYPE",
        {rt: _fake_collector(rt, calls) for rt in azure_orchestrator._COLLECTORS_BY_RESOURCE_TYPE},
    )

    asyncio.run(
        azure_orchestrator.discover_azure_scope(None, "sub-1", resource_types=["route_table"])
    )

    assert set(calls) == {"network", "route_table"}
