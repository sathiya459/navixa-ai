import asyncio
import time

import oci

from app.collectors.base import CollectionResult
from app.collectors.oci.util import to_dict
from app.collectors.retry import with_oci_retry


def _list_vcns_sync(client: oci.core.VirtualNetworkClient, compartment_id: str) -> list:
    return oci.pagination.list_call_get_all_results(client.list_vcns, compartment_id).data


async def collect_vcns(
    client: oci.core.VirtualNetworkClient, compartment_id: str, semaphore
) -> CollectionResult:
    """The OCI SDK is synchronous only; runs in a worker thread (same
    approach as the GCP collectors, which face the same constraint)."""
    start = time.monotonic()
    async with semaphore:
        try:
            vcns = await with_oci_retry(
                lambda: asyncio.to_thread(_list_vcns_sync, client, compartment_id)
            )
            items = [to_dict(vcn) for vcn in vcns]
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
