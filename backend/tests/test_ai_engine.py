import uuid

import pytest

from app.ai_engine.base import AIProviderError
from app.ai_engine.prompts import (
    build_executive_summary_prompt,
    build_recommendation_prompt,
    build_root_cause_prompt,
    build_topology_explanation_prompt,
)
from app.ai_engine.registry import get_provider, list_providers
from app.models.finding import Finding


def _finding(**overrides) -> Finding:
    defaults = dict(
        id=uuid.uuid4(),
        audit_job_id=uuid.uuid4(),
        module="validate",
        finding_type="unauthorized_peering",
        severity="high",
        title="Unauthorized VPC peering: pcx-1",
        description="VPC peering connects two spokes.",
        affected_resource_ids=[],
        status="open",
    )
    defaults.update(overrides)
    return Finding(**defaults)


def test_list_providers_returns_all_five():
    providers = list_providers()
    names = {p["provider"] for p in providers}
    assert names == {"claude", "openai", "azure_openai", "gemini", "bedrock"}


def test_providers_report_not_configured_without_keys(monkeypatch):
    from app.config.settings import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "azure_openai_api_key", None)
    monkeypatch.setattr(settings, "gemini_api_key", None)

    for entry in list_providers():
        if entry["provider"] == "bedrock":
            continue  # bedrock is "configured" once a model/region default exists
        assert entry["configured"] is False


def test_get_unknown_provider_raises():
    with pytest.raises(AIProviderError):
        get_provider("does-not-exist")


def test_root_cause_prompt_includes_finding_details():
    finding = _finding()
    system, user = build_root_cause_prompt(finding)
    assert "NAVIXA InsightAI" in system
    assert "unauthorized_peering" in user
    assert finding.title in user


def test_recommendation_prompt_asks_for_steps():
    finding = _finding()
    _, user = build_recommendation_prompt(finding)
    assert "step-by-step" in user


def test_executive_summary_prompt_handles_no_findings():
    _, user = build_executive_summary_prompt([])
    assert "No findings were identified." in user


def test_executive_summary_prompt_includes_severity_breakdown():
    findings = [_finding(severity="critical"), _finding(severity="high")]
    _, user = build_executive_summary_prompt(findings)
    assert "critical" in user
    assert "high" in user


def test_topology_explanation_prompt_includes_summary():
    _, user = build_topology_explanation_prompt("unauthorized_peering: 2")
    assert "unauthorized_peering: 2" in user
