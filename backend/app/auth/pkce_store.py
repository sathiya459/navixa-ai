"""Short-lived state for the delegated environment-connection SSO device
flow (app/api/v1/delegated_auth.py) - both Azure and AWS authenticate via
the OAuth 2.0 Device Authorization Grant (RFC 8628), so a device flow's
`device_code`/client credentials must survive multiple poll requests (not
single-use), with a TTL matching the IdP's own `expires_in` for that flow.

Backed by Redis (already required for Celery, app/workers/celery_app.py)
rather than the request-response cycle itself, since the frontend polls
`/device/poll` repeatedly across separate HTTP requests while the admin
completes sign-in elsewhere.
"""

import json
import secrets

import redis.asyncio as redis

from app.config.settings import get_settings


def _client() -> redis.Redis:
    settings = get_settings()
    return redis.from_url(settings.redis_url)


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
