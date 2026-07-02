"""AWS credential broker and async session factory for NAVIXA Discover.

Phase 1 uses a stubbed AssumeRole exchange so the collector pipeline can be
built and tested end-to-end without a live AWS Org. Phase 5 (Section 8)
replaces `assume_role_for_scope` with a real STS AssumeRole call via
IAM Identity Center — no long-lived access keys are ever persisted.
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
    """Stub: exchange federated identity for temporary, scoped AWS credentials.

    Real implementation calls sts:AssumeRole against a per-account audit
    role using the platform's IAM Identity Center federation, returning
    short-lived credentials that are never written to disk or logs.
    """
    return ScopedCredentials(
        access_key="stub-access-key",
        secret_key="stub-secret-key",
        session_token="stub-session-token",
        region=region,
    )


def get_async_session(creds: ScopedCredentials) -> aioboto3.Session:
    return aioboto3.Session(
        aws_access_key_id=creds.access_key,
        aws_secret_access_key=creds.secret_key,
        aws_session_token=creds.session_token,
        region_name=creds.region,
    )
