import asyncio
import time

from google.cloud.compute_v1.services.firewalls import FirewallsClient

from app.collectors.base import CollectionResult
from app.collectors.gcp.util import proto_to_dict
from app.collectors.retry import with_gcp_retry


async def collect_firewall_rules(
    client: FirewallsClient, project_id: str, semaphore
) -> CollectionResult:
    start = time.monotonic()
    async with semaphore:
        try:
            rules = await with_gcp_retry(
                lambda: asyncio.to_thread(lambda: list(client.list(project=project_id)))
            )
            items = [proto_to_dict(rule) for rule in rules]
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
