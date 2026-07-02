"""AWS credential broker and async session factory for NAVIXA Discover
(Section 8): calls sts:AssumeRole against a per-account audit role, using
whatever identity the platform itself runs as (IAM Identity Center
permission set, instance profile, or CI/CD role) as the calling principal.
No long-lived access keys are ever configured or persisted - only the
short-lived credentials AssumeRole returns, held in memory for the
duration of one discovery run.
"""

import aioboto3

from app.config.settings import get_settings

settings = get_settings()


class ScopedCredentials:
    def __init__(self, access_key: str, secret_key: str, session_token: str, region: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self.session_token = session_token
        self.region = region


async def assume_role_for_scope(external_scope_id: str, region: str) -> ScopedCredentials:
    """Assumes `settings.aws_audit_role_name` in the target account
    (`external_scope_id`). The calling identity must already be permitted
    to assume that role - typically granted via an IAM Identity Center
    permission set or a trust policy scoped to the platform's own role.
    """
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


def get_async_session(creds: ScopedCredentials) -> aioboto3.Session:
    return aioboto3.Session(
        aws_access_key_id=creds.access_key,
        aws_secret_access_key=creds.secret_key,
        aws_session_token=creds.session_token,
        region_name=creds.region,
    )
