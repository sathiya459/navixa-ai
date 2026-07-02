import asyncio
import time

import oci

from app.collectors.base import CollectionResult
from app.collectors.oci.util import to_dict
from app.collectors.retry import with_oci_retry


def _list_security_lists_sync(client: oci.core.VirtualNetworkClient, compartment_id: str) -> list:
    return oci.pagination.list_call_get_all_results(
        client.list_security_lists, compartment_id
    ).data


async def collect_security_lists(
    client: oci.core.VirtualNetworkClient, compartment_id: str, semaphore
) -> CollectionResult:
    start = time.monotonic()
    async with semaphore:
        try:
            security_lists = await with_oci_retry(
                lambda: asyncio.to_thread(_list_security_lists_sync, client, compartment_id)
            )
            items = [to_dict(sl) for sl in security_lists]
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
