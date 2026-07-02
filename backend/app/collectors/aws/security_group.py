import time

import aioboto3

from app.collectors.base import CollectionResult
from app.collectors.retry import with_retry


async def collect_security_groups(session: aioboto3.Session, semaphore) -> CollectionResult:
    start = time.monotonic()
    async with semaphore:
        try:
            async with session.client("ec2") as ec2:
                response = await with_retry(lambda: ec2.describe_security_groups())
            items = response.get("SecurityGroups", [])
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
