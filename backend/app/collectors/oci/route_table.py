import asyncio
import time

import oci

from app.collectors.base import CollectionResult
from app.collectors.oci.util import to_dict
from app.collectors.retry import with_oci_retry


def _list_route_tables_sync(client: oci.core.VirtualNetworkClient, compartment_id: str) -> list:
    return oci.pagination.list_call_get_all_results(client.list_route_tables, compartment_id).data


async def collect_route_tables(
    client: oci.core.VirtualNetworkClient, compartment_id: str, semaphore
) -> CollectionResult:
    start = time.monotonic()
    async with semaphore:
        try:
            route_tables = await with_oci_retry(
                lambda: asyncio.to_thread(_list_route_tables_sync, client, compartment_id)
            )
            items = [to_dict(rt) for rt in route_tables]
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
