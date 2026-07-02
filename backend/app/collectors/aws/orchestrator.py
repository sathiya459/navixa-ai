"""Per-scope AWS discovery fan-out (Section 10a).

Runs all resource-type collectors concurrently for a single account, bounded
by per-resource-type semaphores, and returns partial results with per-type
status rather than raising on the first failure.
"""

import asyncio

from app.collectors.aws.client import assume_role_for_scope, get_async_session
from app.collectors.aws.gateway import collect_gateways
from app.collectors.aws.peering import collect_peering_connections
from app.collectors.aws.route_table import collect_route_tables
from app.collectors.aws.security_group import collect_security_groups
from app.collectors.aws.subnet import collect_subnets
from app.collectors.aws.vpc import collect_vpcs as collect_networks
from app.collectors.base import CollectionResult
from app.config.rate_limits import AWS_RATE_LIMITS


async def discover_aws_scope(external_scope_id: str, region: str) -> list[CollectionResult]:
    """Fan out all AWS resource-type collectors for one account, concurrently."""
    creds = await assume_role_for_scope(external_scope_id, region)
    session = get_async_session(creds, region)

    semaphores = {
        resource_type: asyncio.Semaphore(limit)
        for resource_type, limit in AWS_RATE_LIMITS.items()
    }

    tasks = [
        collect_networks(session, semaphores["network"]),
        collect_subnets(session, semaphores["subnet"]),
        collect_route_tables(session, semaphores["route_table"]),
        collect_security_groups(session, semaphores["security_group"]),
        collect_gateways(session, semaphores["gateway"]),
        collect_peering_connections(session, semaphores["peering_connection"]),
    ]

    # return_exceptions=True: one collector's bug/unhandled error must not
    # abort discovery for the other resource types (fault isolation, Section 10a #4).
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return [
        result
        if isinstance(result, CollectionResult)
        else CollectionResult(resource_type="unknown", status="failed", error_detail=str(result))
        for result in results
    ]


async def discover_aws_scopes(
    scopes: list[tuple[str, str]], max_parallel_scopes: int = 5
) -> dict[str, list[CollectionResult]]:
    """Fan out discovery across multiple AWS accounts concurrently.

    `scopes` is a list of (external_scope_id, region) tuples. Each scope's
    failure is isolated: one account timing out does not block the others.
    """
    scope_semaphore = asyncio.Semaphore(max_parallel_scopes)

    async def _run_scope(external_scope_id: str, region: str):
        async with scope_semaphore:
            return external_scope_id, await discover_aws_scope(external_scope_id, region)

    results = await asyncio.gather(
        *(_run_scope(scope_id, region) for scope_id, region in scopes)
    )
    return dict(results)
