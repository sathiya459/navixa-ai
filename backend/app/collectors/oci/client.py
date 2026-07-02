"""OCI credential broker for NAVIXA Discover.

Phase 2 stubs the OCI Federation / Identity Domains exchange (Section 8)
the same way the other three providers are stubbed. Phase 5 replaces
`get_scoped_config` with a real federation token exchange; no long-lived
API signing keys are persisted.

Like AWS/Azure/GCP, the OCI Python SDK's compartment/VCN clients are
synchronous only, so collectors run them via asyncio.to_thread.
"""

import oci
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# The OCI SDK validates that `key_content` parses as a real private key at
# client-construction time, unlike AWS/Azure/GCP's stub credentials (which
# aren't validated until an actual API call is made). A throwaway key here
# keeps the stub non-throwing, consistent with the other three providers.
_STUB_KEY_PEM = serialization.PrivateFormat.TraditionalOpenSSL
_STUB_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


async def get_scoped_config(external_scope_id: str, region: str) -> dict:
    """Stub: exchange federated identity for a scoped OCI client config."""
    key_pem = _STUB_PRIVATE_KEY.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=_STUB_KEY_PEM,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    return {
        "tenancy": f"ocid1.tenancy.oc1..{external_scope_id}",
        "user": "ocid1.user.oc1..aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "fingerprint": "20:3b:97:13:55:1c:5b:0d:d3:37:d8:50:4e:c5:3a:34",
        "key_content": key_pem,
        "region": region,
    }


def get_network_client(config: dict) -> oci.core.VirtualNetworkClient:
    return oci.core.VirtualNetworkClient(config)
