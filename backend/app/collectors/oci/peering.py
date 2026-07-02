import asyncio
import time

import oci

from app.collectors.base import CollectionResult
from app.collectors.oci.util import to_dict
from app.collectors.retry import with_oci_retry


def _list_lpgs_sync(client: oci.core.VirtualNetworkClient, compartment_id: str) -> list:
    """Local Peering Gateways are OCI's VCN peering mechanism (Section 10 OCI scope)."""
    return oci.pagination.list_call_get_all_results(
        client.list_local_peering_gateways, compartment_id
    ).data


async def collect_peering_connections(
    client: oci.core.VirtualNetworkClient, compartment_id: str, semaphore
) -> CollectionResult:
    start = time.monotonic()
    async with semaphore:
        try:
            lpgs = await with_oci_retry(
                lambda: asyncio.to_thread(_list_lpgs_sync, client, compartment_id)
            )
            items = [to_dict(lpg) for lpg in lpgs]
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
