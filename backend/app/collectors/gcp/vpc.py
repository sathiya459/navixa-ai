import asyncio
import time

from google.cloud.compute_v1.services.networks import NetworksClient

from app.collectors.base import CollectionResult
from app.collectors.gcp.util import proto_to_dict
from app.collectors.retry import with_gcp_retry


async def collect_networks(client: NetworksClient, project_id: str, semaphore) -> CollectionResult:
    """google-cloud-compute has no async transport (REST-only API, no gRPC),
    so the sync client is run in a worker thread via asyncio.to_thread to
    keep this collector non-blocking within the fan-out (Section 10a).
    """
    start = time.monotonic()
    async with semaphore:
        try:
            networks = await with_gcp_retry(
                lambda: asyncio.to_thread(lambda: list(client.list(project=project_id)))
            )
            items = [proto_to_dict(network) for network in networks]
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
