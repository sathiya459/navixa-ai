"""Short-lived (state -> PKCE code_verifier, scope_key) mapping for the
delegated environment-connection SSO popup flow
(app/api/v1/delegated_auth.py). `scope_key` is the environment name
("dev"/"prod") the popup was started for.

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


async def create_state(scope_key: str, provider: str, code_verifier: str) -> str:
    state = secrets.token_urlsafe(24)
    payload = json.dumps({"scope_key": scope_key, "provider": provider, "code_verifier": code_verifier})
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


# --- Device authorization grant state (Azure device-code flow) -----------
#
# Separate from the PKCE state above: a device flow's `device_code` must
# survive multiple poll requests (not single-use), so it gets its own TTL
# matching Azure AD's own `expires_in` for that flow instead of the fixed
# PKCE window.

_DEVICE_FLOW_KEY_PREFIX = "navixa:device-flow-state:"


async def create_device_flow_state(payload: dict, ttl_seconds: int) -> str:
    flow_id = secrets.token_urlsafe(24)
    client = _client()
    try:
        await client.set(f"{_DEVICE_FLOW_KEY_PREFIX}{flow_id}", json.dumps(payload), ex=ttl_seconds)
    finally:
        await client.aclose()
    return flow_id


async def get_device_flow_state(flow_id: str) -> dict | None:
    client = _client()
    try:
        payload = await client.get(f"{_DEVICE_FLOW_KEY_PREFIX}{flow_id}")
        return json.loads(payload) if payload is not None else None
    finally:
        await client.aclose()


async def delete_device_flow_state(flow_id: str) -> None:
    client = _client()
    try:
        await client.delete(f"{_DEVICE_FLOW_KEY_PREFIX}{flow_id}")
    finally:
        await client.aclose()
