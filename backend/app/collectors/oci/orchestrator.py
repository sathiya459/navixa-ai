"""Per-scope OCI discovery fan-out (Section 10a), mirroring the other three orchestrators."""

import asyncio

from app.collectors.base import CollectionResult
from app.collectors.oci.client import get_network_client, get_scoped_config
from app.collectors.oci.peering import collect_peering_connections
from app.collectors.oci.route_table import collect_route_tables
from app.collectors.oci.security_list import collect_security_lists
from app.collectors.oci.subnet import collect_subnets
from app.collectors.oci.vcn import collect_vcns
from app.config.rate_limits import OCI_RATE_LIMITS


async def discover_oci_scope(compartment_id: str, region: str) -> list[CollectionResult]:
    """Fan out all OCI resource-type collectors for one compartment, concurrently."""
    config = await get_scoped_config(compartment_id, region)
    network_client = get_network_client(config)

    semaphores = {
        resource_type: asyncio.Semaphore(limit)
        for resource_type, limit in OCI_RATE_LIMITS.items()
    }

    tasks = [
        collect_vcns(network_client, compartment_id, semaphores["network"]),
        collect_subnets(network_client, compartment_id, semaphores["subnet"]),
        collect_route_tables(network_client, compartment_id, semaphores["route_table"]),
        collect_security_lists(network_client, compartment_id, semaphores["security_group"]),
        collect_peering_connections(network_client, compartment_id, semaphores["peering_connection"]),
    ]

    # return_exceptions=True: fault isolation across resource types (Section 10a #4).
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return [
        result
        if isinstance(result, CollectionResult)
        else CollectionResult(resource_type="unknown", status="failed", error_detail=str(result))
        for result in results
    ]


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
