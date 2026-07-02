"""PKCE state store tests use an in-memory fake Redis client rather than a
live Redis connection, matching this project's existing test-suite
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


def test_generate_pkce_pair_produces_matching_challenge():
    import base64
    import hashlib

    verifier, challenge = pkce_store.generate_pkce_pair()
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    assert challenge == expected


def test_create_and_consume_state_round_trip():
    state = asyncio.run(pkce_store.create_state("tenant-1", "azure", "verifier-abc"))
    payload = asyncio.run(pkce_store.consume_state(state))
    assert payload == {"tenant_id": "tenant-1", "provider": "azure", "code_verifier": "verifier-abc"}


def test_consume_state_is_single_use():
    state = asyncio.run(pkce_store.create_state("tenant-1", "aws", "verifier-xyz"))
    asyncio.run(pkce_store.consume_state(state))
    assert asyncio.run(pkce_store.consume_state(state)) is None


def test_consume_state_returns_none_for_unknown_state():
    assert asyncio.run(pkce_store.consume_state("does-not-exist")) is None
