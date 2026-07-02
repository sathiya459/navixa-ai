import asyncio
import time

from google.cloud.compute_v1.services.networks import NetworksClient

from app.collectors.base import CollectionResult
from app.collectors.gcp.util import proto_to_dict
from app.collectors.retry import with_gcp_retry


def _list_all_sync(client: NetworksClient, project_id: str) -> list[dict]:
    items = []
    for network in client.list(project=project_id):
        for peering in network.peerings or []:
            items.append({**proto_to_dict(peering), "network": network.self_link})
    return items


async def collect_peering_connections(
    client: NetworksClient, project_id: str, semaphore
) -> CollectionResult:
    """GCP network peerings are embedded in the Network resource's `peerings`
    field (there is no standalone peering-connection list API).
    """
    start = time.monotonic()
    async with semaphore:
        try:
            items = await with_gcp_retry(
                lambda: asyncio.to_thread(_list_all_sync, client, project_id)
            )
            return CollectionResult(
                resource_type="peering_connection",
                status="success",
                items=items,
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        except Exception as exc:  # noqa: BLE001
            return CollectionResult(
                resource_type="peering_connection",
                status="failed",
                error_detail=str(exc),
                duration_ms=int((time.monotonic() - start) * 1000),
            )
