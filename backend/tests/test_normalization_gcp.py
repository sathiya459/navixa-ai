from app.collectors.base import CollectionResult
from app.collectors.normalization import normalize_results


def test_normalize_gcp_network_uses_self_link():
    results = [
        CollectionResult(
            resource_type="network",
            status="success",
            items=[{"selfLink": "https://.../networks/prod-vpc", "name": "prod-vpc"}],
        )
    ]
    normalized = normalize_results(results, "gcp")
    assert normalized[0]["native_id"] == "https://.../networks/prod-vpc"
    assert normalized[0]["name"] == "prod-vpc"
    assert normalized[0]["provider"] == "gcp"


def test_normalize_gcp_peering_uses_name():
    results = [
        CollectionResult(
            resource_type="peering_connection",
            status="success",
            items=[{"name": "peer-1", "network": "vpc-a"}],
        )
    ]
    normalized = normalize_results(results, "gcp")
    assert normalized[0]["native_id"] == "peer-1"
