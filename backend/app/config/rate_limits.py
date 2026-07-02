"""Per-provider, per-resource-type concurrency limits for NAVIXA Discover.

Values are max concurrent in-flight API calls, not requests-per-second;
combined with retry/backoff in collectors/aws/orchestrator.py to stay
under each provider's throttling thresholds.
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

MAX_PARALLEL_SCOPES: dict[str, int] = {
    "aws": 5,
    "azure": 5,
    "gcp": 5,
    "oci": 5,
}
