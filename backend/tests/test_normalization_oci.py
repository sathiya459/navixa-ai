from app.collectors.base import CollectionResult
from app.collectors.normalization import normalize_results


def test_normalize_oci_network_uses_id_and_display_name():
    results = [
        CollectionResult(
            resource_type="network",
            status="success",
            items=[{"id": "ocid1.vcn.oc1..aaaa", "display_name": "prod-vcn"}],
        )
    ]
    normalized = normalize_results(results, "oci")
    assert normalized[0]["native_id"] == "ocid1.vcn.oc1..aaaa"
    assert normalized[0]["name"] == "prod-vcn"
    assert normalized[0]["provider"] == "oci"
