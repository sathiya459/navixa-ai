"""Per-scope OCI discovery fan-out (Section 10a), mirroring the other three orchestrators."""

import asyncio
from collections.abc import Awaitable, Callable

from app.collectors.base import CollectionResult, run_collectors_with_progress
from app.collectors.oci.client import get_network_client, get_scoped_config
from app.collectors.oci.peering import collect_peering_connections
from app.collectors.oci.route_table import collect_route_tables
from app.collectors.oci.security_list import collect_security_lists
from app.collectors.oci.subnet import collect_subnets
from app.collectors.oci.vcn import collect_vcns
from app.config.rate_limits import OCI_RATE_LIMITS

_RESOURCE_TYPES = {"network", "subnet", "route_table", "security_group", "peering_connection"}


def expected_resource_types() -> set[str]:
    """See aws/orchestrator.py's function of the same name. OCI has no
    `resource_types` filtering yet, so this is always the full set."""
    return set(_RESOURCE_TYPES)


async def discover_oci_scope(
    compartment_id: str,
    region: str,
    on_result: Callable[[CollectionResult], Awaitable[None]] | None = None,
) -> list[CollectionResult]:
    """Fan out all OCI resource-type collectors for one compartment, concurrently."""
    config = await get_scoped_config(compartment_id, region)
    network_client = get_network_client(config)

    semaphores = {
        resource_type: asyncio.Semaphore(limit)
        for resource_type, limit in OCI_RATE_LIMITS.items()
    }

    collectors = {
        "network": collect_vcns(network_client, compartment_id, semaphores["network"]),
        "subnet": collect_subnets(network_client, compartment_id, semaphores["subnet"]),
        "route_table": collect_route_tables(
            network_client, compartment_id, semaphores["route_table"]
        ),
        "security_group": collect_security_lists(
            network_client, compartment_id, semaphores["security_group"]
        ),
        "peering_connection": collect_peering_connections(
            network_client, compartment_id, semaphores["peering_connection"]
        ),
    }

    return await run_collectors_with_progress(collectors, on_result)


async def discover_oci_scopes(
    scopes: list[tuple[str, str]], max_parallel_scopes: int = 5
) -> dict[str, list[CollectionResult]]:
    """Fan out discovery across multiple OCI compartments concurrently."""
    scope_semaphore = asyncio.Semaphore(max_parallel_scopes)

    async def _run_scope(compartment_id: str, region: str):
        async with scope_semaphore:
            return compartment_id, await discover_oci_scope(compartment_id, region)

    results = await asyncio.gather(
        *(_run_scope(compartment_id, region) for compartment_id, region in scopes)
    )
    return dict(results)
