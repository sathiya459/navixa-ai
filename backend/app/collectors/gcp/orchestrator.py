"""Per-scope GCP discovery fan-out (Section 10a), mirroring the AWS/Azure orchestrators."""

import asyncio
from collections.abc import Awaitable, Callable

from google.cloud.compute_v1.services.firewalls import FirewallsClient
from google.cloud.compute_v1.services.networks import NetworksClient
from google.cloud.compute_v1.services.routes import RoutesClient
from google.cloud.compute_v1.services.subnetworks import SubnetworksClient

from app.collectors.base import CollectionResult, run_collectors_with_progress
from app.collectors.gcp.client import get_scoped_credential
from app.collectors.gcp.firewall import collect_firewall_rules
from app.collectors.gcp.peering import collect_peering_connections
from app.collectors.gcp.route import collect_routes
from app.collectors.gcp.subnet import collect_subnets
from app.collectors.gcp.vpc import collect_networks
from app.config.rate_limits import GCP_RATE_LIMITS

_RESOURCE_TYPES = {"network", "subnet", "route_table", "security_group", "peering_connection"}


def expected_resource_types() -> set[str]:
    """See aws/orchestrator.py's function of the same name. GCP has no
    `resource_types` filtering yet, so this is always the full set."""
    return set(_RESOURCE_TYPES)


async def discover_gcp_scope(
    project_id: str,
    on_result: Callable[[CollectionResult], Awaitable[None]] | None = None,
) -> list[CollectionResult]:
    """Fan out all GCP resource-type collectors for one project, concurrently."""
    credentials = await get_scoped_credential(project_id)

    networks_client = NetworksClient(credentials=credentials)
    subnets_client = SubnetworksClient(credentials=credentials)
    routes_client = RoutesClient(credentials=credentials)
    firewalls_client = FirewallsClient(credentials=credentials)

    semaphores = {
        resource_type: asyncio.Semaphore(limit)
        for resource_type, limit in GCP_RATE_LIMITS.items()
    }

    collectors = {
        "network": collect_networks(networks_client, project_id, semaphores["network"]),
        "subnet": collect_subnets(subnets_client, project_id, semaphores["subnet"]),
        "route_table": collect_routes(routes_client, project_id, semaphores["route_table"]),
        "security_group": collect_firewall_rules(
            firewalls_client, project_id, semaphores["security_group"]
        ),
        "peering_connection": collect_peering_connections(
            networks_client, project_id, semaphores["peering_connection"]
        ),
    }

    return await run_collectors_with_progress(collectors, on_result)


async def discover_gcp_scopes(
    project_ids: list[str], max_parallel_scopes: int = 5
) -> dict[str, list[CollectionResult]]:
    """Fan out discovery across multiple GCP projects concurrently."""
    scope_semaphore = asyncio.Semaphore(max_parallel_scopes)

    async def _run_scope(project_id: str):
        async with scope_semaphore:
            return project_id, await discover_gcp_scope(project_id)

    results = await asyncio.gather(*(_run_scope(project_id) for project_id in project_ids))
    return dict(results)
