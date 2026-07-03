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
from app.models.environment_connection import EnvironmentConnection


_COLLECTORS_BY_RESOURCE_TYPE = {
    "network": collect_vnets,
    "subnet": collect_subnets,
    "route_table": collect_route_tables,
    "security_group": collect_network_security_groups,
    "peering_connection": collect_peering_connections,
}


async def discover_azure_scope(
    connection: EnvironmentConnection | None,
    external_scope_id: str,
    resource_types: list[str] | None = None,
) -> list[CollectionResult]:
    """Fan out Azure resource-type collectors for one subscription,
    concurrently. See discover_aws_scope's docstring for `resource_types`
    semantics - identical here."""
    credential = get_scoped_credential(connection)
    network_client = get_network_client(credential, subscription_id=external_scope_id)

    semaphores = {
        resource_type: asyncio.Semaphore(limit)
        for resource_type, limit in AZURE_RATE_LIMITS.items()
    }

    selected_types = set(resource_types) | {"network"} if resource_types else set(
        _COLLECTORS_BY_RESOURCE_TYPE
    )

    # Both the client and the credential itself hold an aiohttp session -
    # closing only network_client (as before) leaked the credential's
    # session, surfaced by aiohttp's "Unclosed client session" warning
    # during a real discovery run.
    async with network_client, credential:
        tasks = [
            collector(network_client, semaphores[resource_type])
            for resource_type, collector in _COLLECTORS_BY_RESOURCE_TYPE.items()
            if resource_type in selected_types
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
    connection: EnvironmentConnection | None,
    scopes: list[str],
    max_parallel_scopes: int = 5,
    resource_types: list[str] | None = None,
) -> dict[str, list[CollectionResult]]:
    """Fan out discovery across multiple Azure subscriptions concurrently."""
    scope_semaphore = asyncio.Semaphore(max_parallel_scopes)

    async def _run_scope(external_scope_id: str):
        async with scope_semaphore:
            return external_scope_id, await discover_azure_scope(
                connection, external_scope_id, resource_types
            )

    results = await asyncio.gather(*(_run_scope(scope_id) for scope_id in scopes))
    return dict(results)
