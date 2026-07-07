import uuid

from app.ai_engine.deviation_detector import (
    build_deviation_analysis_prompt,
    parse_deviation_response,
    summarize_network_for_ai,
)
from app.models.network_resource import NetworkResource


def _resource(resource_type, native_id, attributes=None, provider="aws"):
    return NetworkResource(
        id=uuid.uuid4(),
        audit_job_scope_id=uuid.uuid4(),
        resource_type=resource_type,
        provider=provider,
        native_id=native_id,
        name=None,
        attributes=attributes or {},
    )


def test_summarize_marks_hub_vs_spoke():
    resources = [_resource("network", "vpc-hub"), _resource("network", "vpc-spoke")]
    summary = summarize_network_for_ai(resources, hub_ids=["vpc-hub"])
    assert "vpc-hub [HUB]" in summary
    assert "vpc-spoke [spoke]" in summary


def test_summarize_includes_open_ingress_flag():
    sg = _resource(
        "security_group",
        "sg-1",
        {"VpcId": "vpc-1", "IpPermissions": [{"IpRanges": [{"CidrIp": "0.0.0.0/0"}]}]},
    )
    summary = summarize_network_for_ai([sg], hub_ids=[])
    assert "open_ingress_from_internet=True" in summary


def test_summarize_includes_azure_peering_endpoints():
    peering = _resource(
        "peering_connection",
        "peer-1",
        {"vnet_id": "vnet-spoke1-dev", "remoteVirtualNetwork": {"id": "vnet-spoke2-dev"}},
        provider="azure",
    )
    summary = summarize_network_for_ai([peering], hub_ids=[])
    assert "peer-1: vnet-spoke1-dev <-> vnet-spoke2-dev" in summary


def test_summarize_includes_azure_open_ingress_flag():
    nsg = _resource(
        "security_group",
        "nsg-1",
        {
            "securityRules": [
                {"direction": "Inbound", "access": "Allow", "destinationAddressPrefix": "*"}
            ]
        },
        provider="azure",
    )
    summary = summarize_network_for_ai([nsg], hub_ids=[])
    assert "open_ingress_from_internet=True" in summary


def test_build_prompt_includes_summary_and_instructions():
    system, user = build_deviation_analysis_prompt("Networks (1):\n  - vpc-1 [HUB]")
    assert "JSON array" in system
    assert "vpc-1 [HUB]" in user


def test_parse_response_handles_clean_json():
    raw = """[{"finding_type": "open_admin_port", "severity": "critical", "title": "SSH open to internet", "description": "Port 22 is open to 0.0.0.0/0.", "affected_resource_ids": ["sg-1"]}]"""
    findings = parse_deviation_response(raw)
    assert len(findings) == 1
    assert findings[0]["finding_type"] == "open_admin_port"
    assert findings[0]["affected_resource_ids"] == ["sg-1"]


def test_parse_response_strips_markdown_fences():
    raw = '```json\n[{"finding_type": "x", "severity": "low", "title": "t", "description": "d"}]\n```'
    findings = parse_deviation_response(raw)
    assert len(findings) == 1
    assert findings[0]["finding_type"] == "x"
    assert findings[0]["affected_resource_ids"] == []


def test_parse_response_returns_empty_for_invalid_json():
    assert parse_deviation_response("not json at all") == []


def test_parse_response_returns_empty_array_when_no_deviations():
    assert parse_deviation_response("[]") == []


def test_parse_response_drops_entries_missing_required_fields():
    raw = '[{"finding_type": "x"}, {"finding_type": "y", "severity": "high", "title": "t", "description": "d"}]'
    findings = parse_deviation_response(raw)
    assert len(findings) == 1
    assert findings[0]["finding_type"] == "y"


def test_parse_response_defaults_invalid_severity_to_medium():
    raw = '[{"finding_type": "x", "severity": "super-bad", "title": "t", "description": "d"}]'
    findings = parse_deviation_response(raw)
    assert findings[0]["severity"] == "medium"


def test_parse_response_ignores_non_list_json():
    assert parse_deviation_response('{"not": "a list"}') == []
