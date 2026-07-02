import time

import aioboto3

from app.collectors.base import CollectionResult
from app.collectors.retry import with_aws_retry


async def collect_peering_connections(session: aioboto3.Session, semaphore) -> CollectionResult:
    start = time.monotonic()
    async with semaphore:
        try:
            async with session.client("ec2") as ec2:
                response = await with_aws_retry(lambda: ec2.describe_vpc_peering_connections())
            items = response.get("VpcPeeringConnections", [])
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
