import asyncio
import time

from google.cloud.compute_v1.services.subnetworks import SubnetworksClient

from app.collectors.base import CollectionResult
from app.collectors.gcp.util import proto_to_dict
from app.collectors.retry import with_gcp_retry


def _list_all_sync(client: SubnetworksClient, project_id: str) -> list:
    items = []
    for _scope, scoped_list in client.aggregated_list(project=project_id):
        items.extend(scoped_list.subnetworks or [])
    return items


async def collect_subnets(client: SubnetworksClient, project_id: str, semaphore) -> CollectionResult:
    """GCP subnets are regional; aggregated_list fetches across all regions in
    one call. Runs the sync client in a worker thread (see vpc.py)."""
    start = time.monotonic()
    async with semaphore:
        try:
            subnets = await with_gcp_retry(
                lambda: asyncio.to_thread(_list_all_sync, client, project_id)
            )
            items = [proto_to_dict(subnet) for subnet in subnets]
            return CollectionResult(
                resource_type="subnet",
                status="success",
                items=items,
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        except Exception as exc:  # noqa: BLE001
            return CollectionResult(
                resource_type="subnet",
                status="failed",
                error_detail=str(exc),
                duration_ms=int((time.monotonic() - start) * 1000),
            )
