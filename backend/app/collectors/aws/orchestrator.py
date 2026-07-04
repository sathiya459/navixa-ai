"""Per-scope AWS discovery fan-out (Section 10a).

Runs all resource-type collectors concurrently for a single account, bounded
by per-resource-type semaphores, and returns partial results with per-type
status rather than raising on the first failure.

Unlike Azure/GCP/OCI - whose list APIs are subscription/project-wide across
every region in one call - AWS's EC2 API is inherently regional
(`ec2.describe_vpcs()` only returns VPCs in the client's configured region).
So each collector here fans out across every region actually enabled on the
account (`_resolve_regions`), not just one hardcoded default, and results
are merged back into one CollectionResult per resource type so upstream
code (progress reporting, status persistence) is unaffected.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable

from app.collectors.aws.client import assume_role_for_scope, get_async_session
from app.collectors.aws.gateway import collect_gateways
from app.collectors.aws.peering import collect_peering_connections
from app.collectors.aws.route_table import collect_route_tables
from app.collectors.aws.security_group import collect_security_groups
from app.collectors.aws.subnet import collect_subnets
from app.collectors.aws.vpc import collect_vpcs as collect_networks
from app.collectors.base import CollectionResult, run_collectors_with_progress
from app.collectors.delegated_auth_errors import DelegatedAuthRequiredError
from app.collectors.retry import with_aws_retry
from app.config.rate_limits import (
    AWS_COLLECTOR_CALL_TIMEOUT_SECONDS,
    AWS_RATE_LIMITS,
    CREDENTIAL_SETUP_TIMEOUT_SECONDS,
)
from app.models.environment_connection import EnvironmentConnection


_COLLECTORS_BY_RESOURCE_TYPE = {
    "network": collect_networks,
    "subnet": collect_subnets,
    "route_table": collect_route_tables,
    "security_group": collect_security_groups,
    "gateway": collect_gateways,
    "peering_connection": collect_peering_connections,
}


def expected_resource_types(resource_types: list[str] | None = None) -> set[str]:
    """The resource-type set `discover_aws_scope` will actually run for a
    given `resource_types` filter - used to compute collection progress
    (N of M types collected) before any collector has completed."""
    if not resource_types:
        return set(_COLLECTORS_BY_RESOURCE_TYPE)
    return (set(resource_types) | {"network"}) & set(_COLLECTORS_BY_RESOURCE_TYPE)


async def _resolve_regions(creds, default_region: str) -> list[str]:
    """Enabled regions for this account (`ec2.describe_regions()` only
    returns opted-in/enabled regions by default, not every AWS region that
    exists). Falls back to just `default_region` if this call fails or
    times out, so a permissions gap or transient error degrades to prior
    (single-region) behavior instead of failing the whole scope."""
    try:
        session = get_async_session(creds, default_region)
        async with session.client("ec2") as ec2:
            response = await asyncio.wait_for(
                with_aws_retry(lambda: ec2.describe_regions()),
                timeout=AWS_COLLECTOR_CALL_TIMEOUT_SECONDS,
            )
        regions = [r["RegionName"] for r in response.get("Regions", [])]
        return regions or [default_region]
    except Exception:  # noqa: BLE001
        return [default_region]


async def _collect_one_region(
    collector, creds, region: str, semaphore, resource_type: str
) -> CollectionResult:
    session = get_async_session(creds, region)
    try:
        result = await asyncio.wait_for(
            collector(session, semaphore), timeout=AWS_COLLECTOR_CALL_TIMEOUT_SECONDS
        )
    except TimeoutError:
        return CollectionResult(
            resource_type=resource_type,
            status="failed",
            error_detail=(
                f"Timed out collecting {resource_type} in {region} after "
                f"{AWS_COLLECTOR_CALL_TIMEOUT_SECONDS}s."
            ),
        )
    for item in result.items:
        item.setdefault("_navixa_region", region)
    return result


async def _collect_across_regions(
    resource_type: str, collector, creds, regions: list[str], semaphore
) -> CollectionResult:
    """Runs one collector once per enabled region and merges the results
    into a single CollectionResult, so callers (progress reporting, status
    persistence) still see one result per resource type rather than one
    per (resource type, region) pair."""
    start = time.monotonic()
    per_region = await asyncio.gather(
        *(
            _collect_one_region(collector, creds, region, semaphore, resource_type)
            for region in regions
        )
    )

    items = [item for result in per_region for item in result.items]
    statuses = {result.status for result in per_region}
    if statuses == {"success"}:
        status = "success"
    elif "success" in statuses:
        status = "partial"
    else:
        status = "failed"

    error_detail = "; ".join(
        f"{region}: {result.error_detail}"
        for region, result in zip(regions, per_region)
        if result.error_detail
    ) or None

    return CollectionResult(
        resource_type=resource_type,
        status=status,
        items=items,
        error_detail=error_detail,
        duration_ms=int((time.monotonic() - start) * 1000),
    )


async def discover_aws_scope(
    connection: EnvironmentConnection | None,
    external_scope_id: str,
    region: str,
    resource_types: list[str] | None = None,
    on_result: Callable[[CollectionResult], Awaitable[None]] | None = None,
) -> list[CollectionResult]:
    """Fan out AWS resource-type collectors for one account, concurrently,
    across every region enabled on that account.

    `resource_types` restricts which collectors actually run (Section: New
    Job Creation Flow "Select Service/Resource Types") - `None` (the
    default, used by scheduled discovery/AI-analysis call sites that don't
    set it) collects everything, matching prior behavior. `network` is
    always included even if omitted, since hub designation in the Validate
    phase requires VPC data to exist.

    `on_result`, if given, is invoked as each resource type finishes rather
    than only once every type in the scope is done - this is what lets a
    job's progress be visible while it's still "stuck" on a slow resource
    type instead of appearing frozen until the entire scope completes.

    Credential/session setup (`assume_role_for_scope`) is bounded by
    `CREDENTIAL_SETUP_TIMEOUT_SECONDS`, and every underlying AWS API call
    (region enumeration, each collector in each region) is bounded by
    `AWS_COLLECTOR_CALL_TIMEOUT_SECONDS` - without these, a stalled SSO/STS
    call or a stalled `ec2.describe_*` call left discovery hung
    indefinitely with no error and no progress at all, since these run
    before any per-type collector result (and thus any status row) exists.
    """
    try:
        creds = await asyncio.wait_for(
            assume_role_for_scope(connection, external_scope_id, region),
            timeout=CREDENTIAL_SETUP_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        return [
            CollectionResult(
                resource_type="_credentials",
                status="failed",
                error_detail=(
                    f"Timed out obtaining AWS credentials for account {external_scope_id} "
                    f"after {CREDENTIAL_SETUP_TIMEOUT_SECONDS}s."
                ),
            )
        ]
    except DelegatedAuthRequiredError:
        # Handled one level up in discover_service._discover_by_provider,
        # which turns this into the standard "reconnect on the Connections
        # page" message - must not be caught by the generic handler below.
        raise
    except Exception as exc:  # noqa: BLE001
        # Anything else here (e.g. a real AccessDenied/InvalidRequest from
        # `sso.get_role_credentials` - often a mismatch between
        # `settings.aws_audit_role_name` and the permission set actually
        # granted to this SSO identity for this account) used to propagate
        # all the way out of this function uncaught. Since `assume_role_for_scope`
        # runs before any per-type collector, no status row exists yet
        # either - the scope looked "stuck running forever" with zero
        # VPCs and no visible error, when it had actually already failed
        # silently. Surfacing it here instead of letting it propagate is
        # the fix; discover_service.run_discovery_for_scope's own
        # try/except is a last-resort safety net for anything that still
        # slips through.
        return [
            CollectionResult(
                resource_type="_credentials",
                status="failed",
                error_detail=f"Failed to obtain AWS credentials for account {external_scope_id}: {exc}",
            )
        ]

    regions = await _resolve_regions(creds, region)

    semaphores = {
        resource_type: asyncio.Semaphore(limit)
        for resource_type, limit in AWS_RATE_LIMITS.items()
    }

    selected_types = expected_resource_types(resource_types)
    collectors = {
        resource_type: _collect_across_regions(
            resource_type, collector, creds, regions, semaphores[resource_type]
        )
        for resource_type, collector in _COLLECTORS_BY_RESOURCE_TYPE.items()
        if resource_type in selected_types
    }

    return await run_collectors_with_progress(collectors, on_result)


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
