import time

from app.collectors.base import CollectionResult
from app.collectors.retry import with_azure_retry


async def collect_vnets(network_client, semaphore) -> CollectionResult:
    start = time.monotonic()
    async with semaphore:
        try:
            async def _list_all():
                return [vnet async for vnet in network_client.virtual_networks.list_all()]

            vnets = await with_azure_retry(_list_all)
            items = [vnet.as_dict() for vnet in vnets]
            return CollectionResult(
                resource_type="network",
                status="success",
                items=items,
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        except Exception as exc:  # noqa: BLE001
            return CollectionResult(
                resource_type="network",
                status="failed",
                error_detail=str(exc),
                duration_ms=int((time.monotonic() - start) * 1000),
            )
