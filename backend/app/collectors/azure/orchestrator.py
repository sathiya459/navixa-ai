"""Per-scope Azure discovery fan-out (Section 10a), mirroring the AWS orchestrator."""

import asyncio

from app.collectors.azure.client import get_network_client, get_scoped_credential
from app.collectors.azure.nsg import collect_network_security_groups
from app.collectors.azure.peering import collect_peering_connections
from app.collectors.azure.route_table import collect_route_tables
from app.collectors.azure.subnet import collect_subnets
from app.collectors.azure.vnet import collect_vnets
from app.collectors.base import CollectionResult
from app.config.rate_limits import AZURE_RATE_LIMITS


async def discover_azure_scope(external_scope_id: str) -> list[CollectionResult]:
    """Fan out all Azure resource-type collectors for one subscription, concurrently."""
    credential = await get_scoped_credential(external_scope_id)
    network_client = get_network_client(credential, subscription_id=external_scope_id)

    semaphores = {
        resource_type: asyncio.Semaphore(limit)
        for resource_type, limit in AZURE_RATE_LIMITS.items()
    }

    # Both the client and the credential itself hold an aiohttp session -
    # closing only network_client (as before) leaked the credential's
    # session, surfaced by aiohttp's "Unclosed client session" warning
    # during a real discovery run.
    async with network_client, credential:
        tasks = [
            collect_vnets(network_client, semaphores["network"]),
            collect_subnets(network_client, semaphores["subnet"]),
            collect_route_tables(network_client, semaphores["route_table"]),
            collect_network_security_groups(network_client, semaphores["security_group"]),
            collect_peering_connections(network_client, semaphores["peering_connection"]),
        ]

        # return_exceptions=True: fault isolation across resource types (Section 10a #4).
        results = await asyncio.gather(*tasks, return_exceptions=True)

    return [
        result
        if isinstance(result, CollectionResult)
        else CollectionResult(resource_type="unknown", status="failed", error_detail=str(result))
        for result in results
    ]


async def discover_azure_scopes(
    scopes: list[str], max_parallel_scopes: int = 5
) -> dict[str, list[CollectionResult]]:
    """Fan out discovery across multiple Azure subscriptions concurrently."""
    scope_semaphore = asyncio.Semaphore(max_parallel_scopes)

    async def _run_scope(external_scope_id: str):
        async with scope_semaphore:
            return external_scope_id, await discover_azure_scope(external_scope_id)

    results = await asyncio.gather(*(_run_scope(scope_id) for scope_id in scopes))
    return dict(results)
