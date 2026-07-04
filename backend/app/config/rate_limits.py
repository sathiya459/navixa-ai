"""Per-provider, per-resource-type concurrency limits for NAVIXA Discover.

Values are max concurrent in-flight API calls, not requests-per-second;
combined with retry/backoff in collectors/aws/orchestrator.py to stay
under each provider's throttling thresholds. For AWS, one resource type's
semaphore is shared across every region scanned for that account (see
`aws/orchestrator.py`'s `_collect_across_regions`) - it bounds total
concurrent calls for that resource type account-wide, not per region.
"""

AWS_RATE_LIMITS: dict[str, int] = {
    "network": 10,
    "subnet": 10,
    "route_table": 10,
    "security_group": 10,
    "gateway": 5,
    "peering_connection": 10,
}

AZURE_RATE_LIMITS: dict[str, int] = {
    "network": 10,
    "subnet": 10,
    "route_table": 10,
    "security_group": 10,
    "peering_connection": 10,
}

GCP_RATE_LIMITS: dict[str, int] = {
    "network": 10,
    "subnet": 10,
    "route_table": 10,
    "security_group": 10,
    "peering_connection": 10,
}

OCI_RATE_LIMITS: dict[str, int] = {
    "network": 10,
    "subnet": 10,
    "route_table": 10,
    "security_group": 10,
    "peering_connection": 10,
}

MAX_PARALLEL_SCOPES: dict[str, int] = {
    "aws": 5,
    "azure": 5,
    "gcp": 5,
    "oci": 5,
}

# Bounds per-scope credential/session setup (assume-role, SSO token
# refresh, scoped-credential acquisition) before any resource-type
# collector even starts - without this, a stalled auth call could hang a
# scope (and the whole audit job) indefinitely with zero progress and no
# error, since it happens before any CollectionResult/status row exists.
CREDENTIAL_SETUP_TIMEOUT_SECONDS = 30

# Bounds a single underlying cloud API call (one collector, one region)
# regardless of how long aioboto3/the provider SDK's own defaults would
# otherwise wait - without this, a stalled `ec2.describe_*` call (or
# similar) could hang a scope, and the whole audit job with it,
# indefinitely with the job stuck showing "discovering" forever.
AWS_COLLECTOR_CALL_TIMEOUT_SECONDS = 60
