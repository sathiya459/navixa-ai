"""Maps raw AWS API responses to the common network model (Section 11)."""

from datetime import datetime, timezone
from typing import Any

from app.collectors.base import CollectionResult


def normalize_aws_results(results: list[CollectionResult]) -> list[dict[str, Any]]:
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
            normalized.append(_normalize_item(result.resource_type, raw, collected_at))

    return normalized


def _normalize_item(resource_type: str, raw: dict[str, Any], collected_at: datetime) -> dict[str, Any]:
    native_id, name = _extract_id_and_name(resource_type, raw)
    return {
        "resource_type": resource_type,
        "provider": "aws",
        "native_id": native_id,
        "name": name,
        "attributes": raw,
        "collected_at": collected_at,
    }


def _extract_id_and_name(resource_type: str, raw: dict[str, Any]) -> tuple[str, str | None]:
    id_keys = {
        "vpc": "VpcId",
        "subnet": "SubnetId",
        "route_table": "RouteTableId",
        "security_group": "GroupId",
        "gateway": "InternetGatewayId",
        "peering_connection": "VpcPeeringConnectionId",
    }
    native_id = raw.get(id_keys.get(resource_type, ""), raw.get("NatGatewayId", "unknown"))

    name = None
    for tag in raw.get("Tags", []) or []:
        if tag.get("Key") == "Name":
            name = tag.get("Value")
            break
    if name is None:
        name = raw.get("GroupName")

    return native_id, name
