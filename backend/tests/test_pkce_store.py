"""Device-flow state store tests use an in-memory fake Redis client rather
than a live Redis connection, matching this project's existing test-suite
convention of not depending on ambient infrastructure (see test_secrets.py,
test_cloud_federation.py)."""

import asyncio

import pytest

from app.auth import pkce_store


class _FakeRedis:
    _store: dict[str, str] = {}

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = value

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def aclose(self) -> None:
        return None


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    fake = _FakeRedis()
    fake._store = {}
    monkeypatch.setattr(pkce_store, "_client", lambda: fake)
    return fake


def test_create_and_get_device_flow_state_round_trip():
    payload = {"tenant_id": "tenant-1", "device_code": "code-abc", "environment": "dev"}
    flow_id = asyncio.run(pkce_store.create_device_flow_state(payload, ttl_seconds=60))
    assert asyncio.run(pkce_store.get_device_flow_state(flow_id)) == payload


def test_get_device_flow_state_returns_none_for_unknown_flow():
    assert asyncio.run(pkce_store.get_device_flow_state("does-not-exist")) is None


def test_delete_device_flow_state_removes_it():
    flow_id = asyncio.run(
        pkce_store.create_device_flow_state({"device_code": "x"}, ttl_seconds=60)
    )
    asyncio.run(pkce_store.delete_device_flow_state(flow_id))
    assert asyncio.run(pkce_store.get_device_flow_state(flow_id)) is None
