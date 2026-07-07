import uuid

from app.hub_spoke_validator.rules import detect_unauthorized_peering
from app.models.network_resource import NetworkResource


def _peering_resource(native_id: str, requester_vpc: str, accepter_vpc: str) -> NetworkResource:
    return NetworkResource(
        id=uuid.uuid4(),
        audit_job_scope_id=uuid.uuid4(),
        resource_type="peering_connection",
        provider="aws",
        native_id=native_id,
        attributes={
            "RequesterVpcInfo": {"VpcId": requester_vpc},
            "AccepterVpcInfo": {"VpcId": accepter_vpc},
        },
    )


def test_flags_peering_not_involving_hub():
    resource = _peering_resource("pcx-1", "vpc-spoke-a", "vpc-spoke-b")
    findings = detect_unauthorized_peering([resource], hub_vpc_ids={"vpc-hub"})
    assert len(findings) == 1
    assert findings[0]["finding_type"] == "unauthorized_peering"


def test_does_not_flag_peering_involving_hub():
    resource = _peering_resource("pcx-2", "vpc-hub", "vpc-spoke-a")
    findings = detect_unauthorized_peering([resource], hub_vpc_ids={"vpc-hub"})
    assert findings == []


def _azure_peering_resource(native_id: str, vnet_id: str, remote_vnet_id: str) -> NetworkResource:
    return NetworkResource(
        id=uuid.uuid4(),
        audit_job_scope_id=uuid.uuid4(),
        resource_type="peering_connection",
        provider="azure",
        native_id=native_id,
        attributes={
            "vnet_id": vnet_id,
            "remoteVirtualNetwork": {"id": remote_vnet_id},
        },
    )


def test_flags_azure_peering_not_involving_hub():
    resource = _azure_peering_resource("peer-1", "vnet-spoke1-dev", "vnet-spoke2-dev")
    findings = detect_unauthorized_peering([resource], hub_vpc_ids={"vnet-hub-dev"})
    assert len(findings) == 1
    assert findings[0]["finding_type"] == "unauthorized_peering"


def test_does_not_flag_azure_peering_involving_hub():
    resource = _azure_peering_resource("peer-2", "vnet-hub-dev", "vnet-spoke1-dev")
    findings = detect_unauthorized_peering([resource], hub_vpc_ids={"vnet-hub-dev"})
    assert findings == []
