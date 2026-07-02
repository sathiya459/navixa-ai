"""GCP credential broker for NAVIXA Discover.

Phase 2 stubs the Workforce Identity Federation exchange (Section 8) the
same way AWS/Azure are stubbed: a scoped, short-lived credential is assumed
here so the collector pipeline can be built and tested without a live GCP
organization. Phase 5 replaces `get_scoped_credential` with a real
Workforce Identity Federation token exchange.
"""

from google.auth.credentials import AnonymousCredentials


async def get_scoped_credential(external_scope_id: str) -> AnonymousCredentials:
    """Stub: exchange federated identity for a scoped GCP credential."""
    return AnonymousCredentials()
