"""Maps raw cloud API responses to the common network model (Section 11)."""

from datetime import datetime, timezone
from typing import Any

from app.collectors.base import CollectionResult

_ID_KEYS_BY_PROVIDER: dict[str, dict[str, str]] = {
    "aws": {
        "network": "VpcId",
        "subnet": "SubnetId",
        "route_table": "RouteTableId",
        "security_group": "GroupId",
        "gateway": "InternetGatewayId",
        "peering_connection": "VpcPeeringConnectionId",
    },
    "azure": {
        "network": "id",
        "subnet": "id",
        "route_table": "id",
        "security_group": "id",
        "peering_connection": "id",
    },
    "gcp": {
        "network": "selfLink",
        "subnet": "selfLink",
        "route_table": "selfLink",
        "security_group": "selfLink",
        "peering_connection": "name",
    },
    "oci": {
        "network": "id",
        "subnet": "id",
        "route_table": "id",
        "security_group": "id",
        "peering_connection": "id",
    },
}


def normalize_results(results: list[CollectionResult], provider: str) -> list[dict[str, Any]]:
    """Flattens successful collector results into common `network_resources` rows.

    Each row matches the NetworkResource model shape (minus audit_job_scope_id,
    which is attached by the caller once the scope context is known).
    """
    normalized: list[dict[str, Any]] = []
    collected_at = datetime.now(timezone.utc)

    for result in results:
        if result.status == "failed":
            continue
        for raw in result.items:
            normalized.append(_normalize_item(result.resource_type, raw, provider, collected_at))

    return normalized


# Backwards-compatible alias for the Phase 1 AWS-only entry point.
def normalize_aws_results(results: list[CollectionResult]) -> list[dict[str, Any]]:
    return normalize_results(results, "aws")


def _normalize_item(
    resource_type: str, raw: dict[str, Any], provider: str, collected_at: datetime
) -> dict[str, Any]:
    native_id, name = _extract_id_and_name(resource_type, raw, provider)
    return {
        "resource_type": resource_type,
        "provider": provider,
        "native_id": native_id,
        "name": name,
        "attributes": raw,
        "collected_at": collected_at,
    }


def _extract_id_and_name(
    resource_type: str, raw: dict[str, Any], provider: str
) -> tuple[str, str | None]:
    id_keys = _ID_KEYS_BY_PROVIDER.get(provider, {})
    native_id = raw.get(id_keys.get(resource_type, ""), raw.get("NatGatewayId", "unknown"))

    name = raw.get("name")
    if name is None:
        for tag in raw.get("Tags", []) or []:
            if tag.get("Key") == "Name":
                name = tag.get("Value")
                break
    if name is None:
        name = raw.get("GroupName")
    if name is None:
        name = raw.get("display_name")

    return native_id, name
