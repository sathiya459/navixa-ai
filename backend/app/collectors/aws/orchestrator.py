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
from app.models.environment_connection import EnvironmentConnection


_COLLECTORS_BY_RESOURCE_TYPE = {
    "network": collect_networks,
    "subnet": collect_subnets,
    "route_table": collect_route_tables,
    "security_group": collect_security_groups,
    "gateway": collect_gateways,
    "peering_connection": collect_peering_connections,
}


async def discover_aws_scope(
    connection: EnvironmentConnection | None,
    external_scope_id: str,
    region: str,
    resource_types: list[str] | None = None,
) -> list[CollectionResult]:
    """Fan out AWS resource-type collectors for one account, concurrently.

    `resource_types` restricts which collectors actually run (Section: New
    Job Creation Flow "Select Service/Resource Types") - `None` (the
    default, used by scheduled discovery/AI-analysis call sites that don't
    set it) collects everything, matching prior behavior. `network` is
    always included even if omitted, since hub designation in the Validate
    phase requires VPC data to exist.
    """
    creds = await assume_role_for_scope(connection, external_scope_id, region)
    session = get_async_session(creds, region)

    semaphores = {
        resource_type: asyncio.Semaphore(limit)
        for resource_type, limit in AWS_RATE_LIMITS.items()
    }

    selected_types = set(resource_types) | {"network"} if resource_types else set(
        _COLLECTORS_BY_RESOURCE_TYPE
    )
    tasks = [
        collector(session, semaphores[resource_type])
        for resource_type, collector in _COLLECTORS_BY_RESOURCE_TYPE.items()
        if resource_type in selected_types
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
    connection: EnvironmentConnection | None,
    scopes: list[tuple[str, str]],
    max_parallel_scopes: int = 5,
    resource_types: list[str] | None = None,
) -> dict[str, list[CollectionResult]]:
    """Fan out discovery across multiple AWS accounts concurrently.

    `scopes` is a list of (external_scope_id, region) tuples. Each scope's
    failure is isolated: one account timing out does not block the others.
    """
    scope_semaphore = asyncio.Semaphore(max_parallel_scopes)

    async def _run_scope(external_scope_id: str, region: str):
        async with scope_semaphore:
            return external_scope_id, await discover_aws_scope(
                connection, external_scope_id, region, resource_types
            )

    results = await asyncio.gather(
        *(_run_scope(scope_id, region) for scope_id, region in scopes)
    )
    return dict(results)
