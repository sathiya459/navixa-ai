import time

from app.collectors.base import CollectionResult
from app.collectors.retry import with_azure_retry


async def collect_route_tables(network_client, semaphore) -> CollectionResult:
    start = time.monotonic()
    async with semaphore:
        try:
            async def _list_all():
                return [rt async for rt in network_client.route_tables.list_all()]

            route_tables = await with_azure_retry(_list_all)
            items = [rt.as_dict() for rt in route_tables]
            return CollectionResult(
                resource_type="route_table",
                status="success",
                items=items,
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        except Exception as exc:  # noqa: BLE001
            return CollectionResult(
                resource_type="route_table",
                status="failed",
                error_detail=str(exc),
                duration_ms=int((time.monotonic() - start) * 1000),
            )
