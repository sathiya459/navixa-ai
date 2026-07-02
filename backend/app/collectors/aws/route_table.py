import time

import aioboto3

from app.collectors.base import CollectionResult
from app.collectors.retry import with_aws_retry


async def collect_route_tables(session: aioboto3.Session, semaphore) -> CollectionResult:
    start = time.monotonic()
    async with semaphore:
        try:
            async with session.client("ec2") as ec2:
                response = await with_aws_retry(lambda: ec2.describe_route_tables())
            items = response.get("RouteTables", [])
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
