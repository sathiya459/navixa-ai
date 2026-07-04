"""Per-connection delegated SSO login (Section 8a): each named
EnvironmentConnection (e.g. "example@abc.com") is signed in independently
and reused across every tenant/account imported through it. This is what
"Sync Accounts" and NAVIXA Discover actually authenticate with in
delegated mode - never the backend host's own CLI session.

Both providers use the OAuth 2.0 Device Authorization Grant (RFC 8628):
the frontend calls `/device/start`, shows the returned code + verification
URL, and polls `/device/poll` until the admin completes sign-in in another
tab/device. This is deliberate for both, not just Azure: IAM Identity
Center's public-client `authorization_code` grant (the popup+redirect
approach this used to use) requires a loopback (127.0.0.1) redirect URI
once the `sso:account:access` scope is requested - see
`RegisterClient`/`CreateToken` in the AWS SSO OIDC API - which a hosted
backend callback can never satisfy. Device code has no redirect URI at
all, so it works the same way for a real IAM Identity Center instance as
it does for Azure AD (see app/collectors/azure/client.py's docstring for
why Azure also can't use a redirect-based flow).
"""

import time
import uuid

import aioboto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.auth.pkce_store import create_device_flow_state, delete_device_flow_state, get_device_flow_state
from app.collectors.aws.client import persist_aws_session
from app.collectors.azure.client import persist_azure_session, poll_device_flow, start_device_flow
from app.config.settings import get_settings
from app.database.session import get_db
from app.models.role import ADMIN
from app.models.user import User
from app.tenant_registry.connection_service import get_connection_by_id

router = APIRouter(prefix="/connections", tags=["Delegated Auth"])
settings = get_settings()


def _get_connection_or_404(db: Session, environment: str, connection_id: uuid.UUID, provider: str):
    connection = get_connection_by_id(db, connection_id)
    if (
        connection is None
        or connection.environment != environment
        or connection.provider != provider
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
    return connection


class DeviceFlowPollRequest(BaseModel):
    flow_id: str


# --- Azure (device code flow) ---------------------------------------------


@router.post("/{environment}/{connection_id}/azure/delegated-auth/device/start")
async def start_azure_device_flow(
    environment: str,
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN)),
) -> dict:
    connection = _get_connection_or_404(db, environment, connection_id, "azure")
    data = await start_device_flow(connection)

    flow_id = await create_device_flow_state(
        {
            "tenant_id": data["tenant_id"],
            "device_code": data["device_code"],
            "environment": environment,
            "connection_id": str(connection_id),
        },
        ttl_seconds=int(data.get("expires_in", 900)),
    )
    return {
        "flow_id": flow_id,
        "user_code": data["user_code"],
        "verification_uri": data.get("verification_uri") or data.get("verification_uri_complete"),
        "expires_in": data.get("expires_in", 900),
        "interval": data.get("interval", 5),
        "message": data.get("message"),
    }


@router.post("/{environment}/{connection_id}/azure/delegated-auth/device/poll")
async def poll_azure_device_flow(
    environment: str,
    connection_id: uuid.UUID,
    payload: DeviceFlowPollRequest,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN)),
) -> dict:
    flow_state = await get_device_flow_state(payload.flow_id)
    if (
        flow_state is None
        or flow_state.get("environment") != environment
        or flow_state.get("connection_id") != str(connection_id)
    ):
        return {"status": "expired"}

    response = await poll_device_flow(flow_state["tenant_id"], flow_state["device_code"])

    error = response.get("error")
    if error in ("authorization_pending", "slow_down"):
        return {"status": "pending"}
    if error:
        await delete_device_flow_state(payload.flow_id)
        return {"status": "error", "message": response.get("error_description", error)}

    connection = get_connection_by_id(db, connection_id)
    if connection is None or connection.environment != environment:
        await delete_device_flow_state(payload.flow_id)
        return {"status": "error", "message": "Connection setup expired, please try again"}

    session = {
        "tenant_id": flow_state["tenant_id"],
        "access_token": response["access_token"],
        "refresh_token": response.get("refresh_token"),
        "access_token_expires_at": int(time.time()) + int(response.get("expires_in", 3600)),
    }
    persist_azure_session(connection, session)
    await delete_device_flow_state(payload.flow_id)
    return {"status": "complete"}


# --- AWS (device code flow) -----------------------------------------------


def _aws_identity_center_region(connection) -> str:
    return connection.region or settings.aws_default_region


async def _get_or_register_sso_client(connection, region: str) -> dict:
    from app.collectors.aws.client import get_sso_session_dict

    existing = get_sso_session_dict(connection)
    if existing and existing.get("client_id") and existing.get("region") == region:
        if existing.get("client_secret_expires_at", 0) > time.time() + 60:
            return existing

    session = aioboto3.Session(region_name=region)
    async with session.client("sso-oidc", region_name=region) as client:
        response = await client.register_client(
            clientName="navixa-ai",
            clientType="public",
            grantTypes=["urn:ietf:params:oauth:grant-type:device_code", "refresh_token"],
        )
    return {
        "region": region,
        "client_id": response["clientId"],
        "client_secret": response["clientSecret"],
        "client_secret_expires_at": response["clientSecretExpiresAt"],
    }


@router.post("/{environment}/{connection_id}/aws/delegated-auth/device/start")
async def start_aws_device_flow(
    environment: str,
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN)),
) -> dict:
    connection = _get_connection_or_404(db, environment, connection_id, "aws")
    if not connection.sso_login_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Set this connection's IAM Identity Center start URL first "
                "(PUT /connections/{environment}/{connection_id})."
            ),
        )
    region = _aws_identity_center_region(connection)

    client_info = await _get_or_register_sso_client(connection, region)
    connection.region = region
    persist_aws_session(connection, client_info)
    db.commit()

    aio_session = aioboto3.Session(region_name=region)
    async with aio_session.client("sso-oidc", region_name=region) as client:
        auth = await client.start_device_authorization(
            clientId=client_info["client_id"],
            clientSecret=client_info["client_secret"],
            startUrl=connection.sso_login_url,
        )

    flow_id = await create_device_flow_state(
        {
            "region": region,
            "client_id": client_info["client_id"],
            "client_secret": client_info["client_secret"],
            "device_code": auth["deviceCode"],
            "environment": environment,
            "connection_id": str(connection_id),
        },
        ttl_seconds=int(auth.get("expiresIn", 600)),
    )
    return {
        "flow_id": flow_id,
        "user_code": auth["userCode"],
        "verification_uri": auth.get("verificationUriComplete") or auth["verificationUri"],
        "expires_in": auth.get("expiresIn", 600),
        "interval": auth.get("interval", 5),
        "message": None,
    }


@router.post("/{environment}/{connection_id}/aws/delegated-auth/device/poll")
async def poll_aws_device_flow(
    environment: str,
    connection_id: uuid.UUID,
    payload: DeviceFlowPollRequest,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role(ADMIN)),
) -> dict:
    flow_state = await get_device_flow_state(payload.flow_id)
    if (
        flow_state is None
        or flow_state.get("environment") != environment
        or flow_state.get("connection_id") != str(connection_id)
    ):
        return {"status": "expired"}

    region = flow_state["region"]
    aio_session = aioboto3.Session(region_name=region)
    try:
        async with aio_session.client("sso-oidc", region_name=region) as client:
            response = await client.create_token(
                clientId=flow_state["client_id"],
                clientSecret=flow_state["client_secret"],
                grantType="urn:ietf:params:oauth:grant-type:device_code",
                deviceCode=flow_state["device_code"],
            )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("AuthorizationPendingException", "SlowDownException"):
            return {"status": "pending"}
        await delete_device_flow_state(payload.flow_id)
        message = exc.response.get("error_description") or code or "Sign-in failed or expired"
        return {"status": "error", "message": message}

    connection = get_connection_by_id(db, connection_id)
    if connection is None or connection.environment != environment:
        await delete_device_flow_state(payload.flow_id)
        return {"status": "error", "message": "Connection setup expired, please try again"}

    session = {
        "region": region,
        "client_id": flow_state["client_id"],
        "client_secret": flow_state["client_secret"],
        "access_token": response["accessToken"],
        "refresh_token": response.get("refreshToken"),
        "access_token_expires_at": int(time.time()) + int(response.get("expiresIn", 28800)),
    }
    persist_aws_session(connection, session)
    await delete_device_flow_state(payload.flow_id)
    return {"status": "complete"}
