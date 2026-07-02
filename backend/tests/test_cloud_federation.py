"""Tests for the Section 8 federation fallback logic: each provider must
keep working with Phase 1/2's stub credentials when its federation config
is unset, and switch to the real path once configured. The real paths
themselves (actual AssumeRole/OAuth/impersonation/session-token calls)
require live cloud accounts and are not exercised here.
"""

import asyncio

import pytest

from app.collectors.azure.client import StubAsyncCredential, get_scoped_credential as azure_get_credential
from app.collectors.azure.client import is_azure_federation_configured
from app.collectors.gcp.client import get_scoped_credential as gcp_get_credential
from app.collectors.gcp.client import is_gcp_federation_configured
from app.collectors.oci.client import get_scoped_config as oci_get_scoped_config
from app.collectors.oci.client import is_oci_federation_configured


def test_azure_falls_back_to_stub_when_unconfigured(monkeypatch):
    from app.collectors.azure import client

    monkeypatch.setattr(client.settings, "azure_federation_tenant_id", None)
    assert is_azure_federation_configured() is False

    credential = asyncio.run(azure_get_credential("sub-1"))
    assert isinstance(credential, StubAsyncCredential)


def test_azure_uses_client_secret_credential_when_configured(monkeypatch):
    from azure.identity.aio import ClientSecretCredential

    from app.collectors.azure import client

    monkeypatch.setattr(client.settings, "azure_federation_tenant_id", "tenant-1")
    monkeypatch.setattr(client.settings, "azure_federation_client_id", "client-1")
    monkeypatch.setattr(client.settings, "azure_federation_client_secret", "secret-1")
    assert is_azure_federation_configured() is True

    credential = asyncio.run(azure_get_credential("sub-1"))
    assert isinstance(credential, ClientSecretCredential)


def test_gcp_falls_back_to_stub_when_unconfigured(monkeypatch):
    from google.auth.credentials import AnonymousCredentials

    from app.collectors.gcp import client

    monkeypatch.setattr(client.settings, "gcp_audit_service_account", None)
    assert is_gcp_federation_configured() is False

    credential = asyncio.run(gcp_get_credential("project-1"))
    assert isinstance(credential, AnonymousCredentials)


def test_gcp_uses_impersonated_credentials_when_configured(monkeypatch):
    from google.auth.impersonated_credentials import Credentials as ImpersonatedCredentials

    from app.collectors.gcp import client

    monkeypatch.setattr(client.settings, "gcp_audit_service_account", "audit@project.iam.gserviceaccount.com")
    assert is_gcp_federation_configured() is True

    from google.auth.credentials import AnonymousCredentials

    monkeypatch.setattr(client, "google_auth_default", lambda: (AnonymousCredentials(), "project-1"))

    credential = asyncio.run(gcp_get_credential("project-1"))
    assert isinstance(credential, ImpersonatedCredentials)


def test_oci_falls_back_to_stub_when_unconfigured(monkeypatch):
    from app.collectors.oci import client

    monkeypatch.setattr(client.settings, "oci_session_token_path", None)
    assert is_oci_federation_configured() is False

    auth = asyncio.run(oci_get_scoped_config("tenancy-1", "us-ashburn-1"))
    assert auth.signer is None
    assert auth.config["tenancy"].startswith("ocid1.tenancy.oc1..")


@pytest.mark.parametrize("configured_path", ["/fake/session_token"])
def test_oci_reports_configured_when_session_token_path_set(monkeypatch, configured_path):
    from app.collectors.oci import client

    monkeypatch.setattr(client.settings, "oci_session_token_path", configured_path)
    assert is_oci_federation_configured() is True
