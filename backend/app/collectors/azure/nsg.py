import time

from app.collectors.base import CollectionResult
from app.collectors.retry import with_azure_retry


async def collect_network_security_groups(network_client, semaphore) -> CollectionResult:
    start = time.monotonic()
    async with semaphore:
        try:
            async def _list_all():
                return [
                    nsg async for nsg in network_client.network_security_groups.list_all()
                ]

            nsgs = await with_azure_retry(_list_all)
            items = [nsg.as_dict() for nsg in nsgs]
            return CollectionResult(
                resource_type="security_group",
                status="success",
                items=items,
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        except Exception as exc:  # noqa: BLE001
            return CollectionResult(
                resource_type="security_group",
                status="failed",
                error_detail=str(exc),
                duration_ms=int((time.monotonic() - start) * 1000),
            )
