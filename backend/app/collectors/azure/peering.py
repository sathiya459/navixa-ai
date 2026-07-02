import time

from app.collectors.base import CollectionResult
from app.collectors.retry import with_azure_retry


async def collect_peering_connections(network_client, semaphore) -> CollectionResult:
    """Azure VNet peerings are sub-resources embedded in each VNet; flattens
    the embedded `virtual_network_peerings` array (see subnet.py for the
    same pattern).
    """
    start = time.monotonic()
    async with semaphore:
        try:
            async def _list_all():
                return [vnet async for vnet in network_client.virtual_networks.list_all()]

            vnets = await with_azure_retry(_list_all)
            items = [
                {**peering.as_dict(), "vnet_id": vnet.id}
                for vnet in vnets
                for peering in (vnet.virtual_network_peerings or [])
            ]
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
