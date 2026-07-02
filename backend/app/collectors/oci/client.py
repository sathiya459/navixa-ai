"""OCI credential broker for NAVIXA Discover (Section 8).

Uses a real session-token-based (federated) signer when
`oci_session_token_path` is configured - matching OCI's documented
Identity Domains federation pattern (`oci session authenticate`
produces a session token + key pair; `SecurityTokenSigner` uses them to
sign requests without a long-lived API key). Falls back to the Phase 2
stub key-pair when unconfigured, so local dev without a real OCI tenancy
keeps working unchanged.

Like AWS/Azure/GCP, the OCI Python SDK's compartment/VCN clients are
synchronous only, so collectors run them via asyncio.to_thread.
"""

from dataclasses import dataclass
from typing import Any

import oci
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.config.settings import get_settings

settings = get_settings()

# The OCI SDK validates that `key_content` parses as a real private key at
# client-construction time, unlike AWS/Azure/GCP's stub credentials (which
# aren't validated until an actual API call is made). A throwaway key here
# keeps the stub non-throwing, consistent with the other three providers.
_STUB_KEY_FORMAT = serialization.PrivateFormat.TraditionalOpenSSL
_STUB_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@dataclass
class OCIAuthContext:
    config: dict
    signer: Any | None = None


def is_oci_federation_configured() -> bool:
    return bool(settings.oci_session_token_path)


async def get_scoped_config(external_scope_id: str, region: str) -> OCIAuthContext:
    if is_oci_federation_configured():
        config = oci.config.from_file(profile_name=settings.oci_config_profile)
        with open(settings.oci_session_token_path, encoding="utf-8") as token_file:
            token = token_file.read().strip()
        private_key = oci.signer.load_private_key_from_file(
            config["key_file"], config.get("pass_phrase")
        )
        signer = oci.auth.signers.SecurityTokenSigner(token, private_key)
        return OCIAuthContext(config={"region": config.get("region", region)}, signer=signer)

    key_pem = _STUB_PRIVATE_KEY.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=_STUB_KEY_FORMAT,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    return OCIAuthContext(
        config={
            "tenancy": f"ocid1.tenancy.oc1..{external_scope_id}",
            "user": "ocid1.user.oc1..aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "fingerprint": "20:3b:97:13:55:1c:5b:0d:d3:37:d8:50:4e:c5:3a:34",
            "key_content": key_pem,
            "region": region,
        }
    )


def get_network_client(auth: OCIAuthContext) -> oci.core.VirtualNetworkClient:
    if auth.signer is not None:
        return oci.core.VirtualNetworkClient(config=auth.config, signer=auth.signer)
    return oci.core.VirtualNetworkClient(auth.config)
