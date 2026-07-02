"""Short-lived (state -> PKCE code_verifier, tenant_id) mapping for the
delegated cloud-tenant SSO popup flow (app/api/v1/delegated_auth.py).

Backed by Redis (already required for Celery, app/workers/celery_app.py)
rather than the request-response cycle itself, since the browser popup
makes the "start" and "callback" requests as two entirely separate HTTP
calls with the IdP redirect in between.
"""

import json
import secrets

import redis.asyncio as redis

from app.config.settings import get_settings

_STATE_TTL_SECONDS = 600
_KEY_PREFIX = "navixa:delegated-auth-state:"


def _client() -> redis.Redis:
    settings = get_settings()
    return redis.from_url(settings.redis_url)


def generate_pkce_pair() -> tuple[str, str]:
    """Returns (code_verifier, code_challenge) for PKCE S256."""
    import base64
    import hashlib

    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge


async def create_state(tenant_id: str, provider: str, code_verifier: str) -> str:
    state = secrets.token_urlsafe(24)
    payload = json.dumps({"tenant_id": tenant_id, "provider": provider, "code_verifier": code_verifier})
    client = _client()
    try:
        await client.set(f"{_KEY_PREFIX}{state}", payload, ex=_STATE_TTL_SECONDS)
    finally:
        await client.aclose()
    return state


async def consume_state(state: str) -> dict | None:
    """Returns the stored payload and deletes it (single use), or None if
    the state is unknown/expired."""
    client = _client()
    try:
        key = f"{_KEY_PREFIX}{state}"
        payload = await client.get(key)
        if payload is None:
            return None
        await client.delete(key)
        return json.loads(payload)
    finally:
        await client.aclose()
