import asyncio
import time

import aioboto3

from app.collectors.base import CollectionResult
from app.collectors.retry import with_retry


async def collect_gateways(session: aioboto3.Session, semaphore) -> CollectionResult:
    """Collects Internet Gateways and NAT Gateways (Section 10 AWS scope)."""
    start = time.monotonic()
    async with semaphore:
        try:
            async with session.client("ec2") as ec2:
                igws_response, nats_response = await with_retry(
                    lambda: _describe_gateways(ec2)
                )
            items = [
                {**igw, "GatewayType": "internet_gateway"}
                for igw in igws_response.get("InternetGateways", [])
            ] + [
                {**nat, "GatewayType": "nat_gateway"}
                for nat in nats_response.get("NatGateways", [])
            ]
            return CollectionResult(
                resource_type="gateway",
                status="success",
                items=items,
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        except Exception as exc:  # noqa: BLE001
            return CollectionResult(
                resource_type="gateway",
                status="failed",
                error_detail=str(exc),
                duration_ms=int((time.monotonic() - start) * 1000),
            )


async def _describe_gateways(ec2):
    igws, nats = await asyncio.gather(
        ec2.describe_internet_gateways(), ec2.describe_nat_gateways()
    )
    return igws, nats
