"""AWS credential broker and async session factory for NAVIXA Discover
(Section 8 / 8a).

Two real modes, selected by `settings.cloud_auth_mode`:
- "delegated": uses the specific CloudTenant's own per-tenant IAM Identity
  Center (AWS SSO) session, captured by the OAuth2 authorization code +
  PKCE popup flow in app/api/v1/delegated_auth.py and stored, encrypted,
  on `CloudTenant.delegated_token_cache`. Resource collection uses
  `sso.GetRoleCredentials` against that session's access token - never the
  backend host's own `aws sso login` profile. Raises
  DelegatedAuthRequiredError if there's no valid cached session.
- "app_only": calls sts:AssumeRole against a per-account audit role, using
  whatever identity the platform itself runs as (IAM Identity Center
  permission set, instance profile, or CI/CD role) as the calling
  principal.

No long-lived access keys are ever configured or persisted - only
short-lived credentials, held in memory for the duration of one
discovery run.
"""

import time

import aioboto3

from app.auth.token_encryption import decrypt, encrypt
from app.collectors.delegated_auth_errors import DelegatedAuthRequiredError
from app.config.settings import get_settings
from app.models.cloud_tenant import CloudTenant

settings = get_settings()


class ScopedCredentials:
    def __init__(self, access_key: str, secret_key: str, session_token: str, region: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self.session_token = session_token
        self.region = region


async def assume_role_for_scope(
    tenant: CloudTenant, external_scope_id: str, region: str
) -> ScopedCredentials | None:
    """Returns None in delegated mode's app_only fallback path is not used
    here anymore - delegated mode now always resolves a concrete
    ScopedCredentials via the tenant's own SSO session
    (get_delegated_role_credentials); otherwise assumes
    `settings.aws_audit_role_name` in the target account
    (`external_scope_id`) via the platform's own calling identity.
    """
    if settings.cloud_auth_mode == "delegated":
        return await get_delegated_role_credentials(tenant, external_scope_id, region)

    role_arn = f"arn:aws:iam::{external_scope_id}:role/{settings.aws_audit_role_name}"
    assume_role_kwargs = {
        "RoleArn": role_arn,
        "RoleSessionName": "navixa-discover",
    }
    if settings.aws_audit_external_id:
        assume_role_kwargs["ExternalId"] = settings.aws_audit_external_id

    session = aioboto3.Session()
    async with session.client("sts", region_name=region) as sts:
        response = await sts.assume_role(**assume_role_kwargs)

    credentials = response["Credentials"]
    return ScopedCredentials(
        access_key=credentials["AccessKeyId"],
        secret_key=credentials["SecretAccessKey"],
        session_token=credentials["SessionToken"],
        region=region,
    )


def get_async_session(creds: ScopedCredentials | None, region: str) -> aioboto3.Session:
    if creds is None:
        return aioboto3.Session(profile_name=settings.aws_profile, region_name=region)

    return aioboto3.Session(
        aws_access_key_id=creds.access_key,
        aws_secret_access_key=creds.secret_key,
        aws_session_token=creds.session_token,
        region_name=creds.region,
    )


def get_org_session(region: str) -> aioboto3.Session:
    """Session for calling AWS Organizations APIs in app_only mode, as the
    platform's own (management/delegated-admin) identity - never a
    per-member-account assumed role. Delegated mode no longer uses this;
    it lists accounts via the tenant's own SSO session instead
    (list_sso_accounts)."""
    return aioboto3.Session(region_name=region)


# --- Per-tenant IAM Identity Center (AWS SSO) delegated auth ---------------
#
# `CloudTenant.delegated_token_cache` (encrypted) holds a JSON blob shaped:
#   {"region": ..., "client_id": ..., "client_secret": ...,
#    "client_secret_expires_at": <epoch>, "access_token": ...,
#    "refresh_token": ..., "access_token_expires_at": <epoch>}
# `region` here is the AWS region hosting the customer's Identity Center
# instance (their sso_login_url's region), not necessarily where resources
# live - GetRoleCredentials/ListAccounts must target that region's `sso`/
# `sso-oidc` endpoints.


def get_sso_session_dict(tenant: CloudTenant) -> dict | None:
    if not tenant.delegated_token_cache:
        return None
    import json

    return json.loads(decrypt(tenant.delegated_token_cache))


def _persist_sso_session(tenant: CloudTenant, session: dict) -> None:
    import json

    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        row = db.get(CloudTenant, tenant.id)
        if row is not None:
            row.delegated_token_cache = encrypt(json.dumps(session))
            db.commit()
    finally:
        db.close()


async def _refresh_sso_access_token(tenant: CloudTenant, session: dict) -> dict:
    aio_session = aioboto3.Session(region_name=session["region"])
    async with aio_session.client("sso-oidc", region_name=session["region"]) as client:
        response = await client.create_token(
            clientId=session["client_id"],
            clientSecret=session["client_secret"],
            grantType="refresh_token",
            refreshToken=session["refresh_token"],
        )
    session["access_token"] = response["accessToken"]
    session["refresh_token"] = response.get("refreshToken", session["refresh_token"])
    session["access_token_expires_at"] = int(time.time()) + int(response.get("expiresIn", 28800))
    _persist_sso_session(tenant, session)
    return session


async def get_valid_sso_session(tenant: CloudTenant) -> dict:
    """Returns a session dict with a non-expired access_token, refreshing
    via the stored refresh_token if needed. Raises
    DelegatedAuthRequiredError if there's no session, or the refresh token
    itself has expired/been revoked (requires a fresh popup login)."""
    session = get_sso_session_dict(tenant)
    if session is None:
        raise DelegatedAuthRequiredError(str(tenant.id), "aws")

    if int(time.time()) < session["access_token_expires_at"] - 60:
        return session

    try:
        return await _refresh_sso_access_token(tenant, session)
    except Exception as exc:
        raise DelegatedAuthRequiredError(str(tenant.id), "aws") from exc


async def get_delegated_role_credentials(
    tenant: CloudTenant, account_id: str, region: str
) -> ScopedCredentials:
    """Mints short-lived credentials for one account via the tenant's own
    SSO session - `settings.aws_audit_role_name` is reused as the IAM
    Identity Center permission-set/role name granted to the SSO
    identity for that account (a naming convention, not an assumed role)."""
    session = await get_valid_sso_session(tenant)
    aio_session = aioboto3.Session(region_name=session["region"])
    async with aio_session.client("sso", region_name=session["region"]) as sso:
        response = await sso.get_role_credentials(
            roleName=settings.aws_audit_role_name,
            accountId=account_id,
            accessToken=session["access_token"],
        )
    creds = response["roleCredentials"]
    return ScopedCredentials(
        access_key=creds["accessKeyId"],
        secret_key=creds["secretAccessKey"],
        session_token=creds["sessionToken"],
        region=region,
    )


async def list_sso_accounts(tenant: CloudTenant) -> list[tuple[str, str]]:
    """Accounts the tenant's SSO session can see, via Identity Center's own
    ListAccounts - not AWS Organizations, so no organizations:* permissions
    are required at all."""
    session = await get_valid_sso_session(tenant)
    aio_session = aioboto3.Session(region_name=session["region"])
    accounts = []
    async with aio_session.client("sso", region_name=session["region"]) as sso:
        paginator = sso.get_paginator("list_accounts")
        async for page in paginator.paginate(accessToken=session["access_token"]):
            for account in page["accountList"]:
                accounts.append((account["accountId"], account.get("accountName") or account["accountId"]))
    return accounts
