from app.collectors.base import CollectionResult
from app.collectors.normalization import normalize_results


def test_normalize_azure_network_uses_resource_id():
    results = [
        CollectionResult(
            resource_type="network",
            status="success",
            items=[{"id": "/subscriptions/x/vnet-1", "name": "prod-vnet"}],
        )
    ]
    normalized = normalize_results(results, "azure")
    assert normalized[0]["native_id"] == "/subscriptions/x/vnet-1"
    assert normalized[0]["name"] == "prod-vnet"
    assert normalized[0]["provider"] == "azure"


def test_normalize_azure_skips_failed_collectors():
    results = [
        CollectionResult(resource_type="subnet", status="failed", error_detail="boom"),
    ]
    normalized = normalize_results(results, "azure")
    assert normalized == []
