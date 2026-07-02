from app.collectors.base import CollectionResult
from app.collectors.normalization import normalize_aws_results


def test_normalize_skips_failed_collectors():
    results = [
        CollectionResult(resource_type="network", status="success", items=[{"VpcId": "vpc-1"}]),
        CollectionResult(resource_type="subnet", status="failed", error_detail="boom"),
    ]
    normalized = normalize_aws_results(results)
    assert len(normalized) == 1
    assert normalized[0]["native_id"] == "vpc-1"
    assert normalized[0]["resource_type"] == "network"
    assert normalized[0]["provider"] == "aws"


def test_normalize_extracts_name_tag():
    results = [
        CollectionResult(
            resource_type="subnet",
            status="success",
            items=[{"SubnetId": "subnet-1", "Tags": [{"Key": "Name", "Value": "prod-subnet"}]}],
        )
    ]
    normalized = normalize_aws_results(results)
    assert normalized[0]["name"] == "prod-subnet"


def test_normalize_handles_partial_status():
    results = [
        CollectionResult(resource_type="network", status="partial", items=[{"VpcId": "vpc-2"}]),
    ]
    normalized = normalize_aws_results(results)
    assert len(normalized) == 1
