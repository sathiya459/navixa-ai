import uuid

from sqlalchemy.orm import Session

from app.ai_engine.deviation_detector import detect_deviations_via_ai
from app.hub_spoke_validator.graph_builder import build_network_graph
from app.hub_spoke_validator.rules import (
    detect_hub_bypass_routing,
    detect_segmentation_violations,
    detect_unauthorized_peering,
    extract_environment_tags,
)
from app.models.audit_job import AuditJob, AuditJobScope
from app.models.finding import Finding
from app.models.network_resource import NetworkResource


def _get_job_resources(db: Session, audit_job_id: uuid.UUID) -> list[NetworkResource]:
    return (
        db.query(NetworkResource)
        .join(AuditJobScope, NetworkResource.audit_job_scope_id == AuditJobScope.id)
        .filter(AuditJobScope.audit_job_id == audit_job_id)
        .all()
    )


def run_validation(db: Session, audit_job: AuditJob, hub_vpc_ids: list[str]) -> list[Finding]:
    """NAVIXA Validate's deterministic rule engine (Section 13): the same
    input always produces the same findings, and every finding traces back
    to an explicit, auditable rule."""
    audit_job.status = "validating"
    audit_job.hub_selection = {"hub_ids": hub_vpc_ids}
    db.commit()

    resources = _get_job_resources(db, audit_job.id)

    hub_ids = set(hub_vpc_ids)
    peering_resources = [r for r in resources if r.resource_type == "peering_connection"]
    network_resources = [r for r in resources if r.resource_type == "network"]
    graph = build_network_graph(resources)
    environments = extract_environment_tags(network_resources)

    raw_findings = [
        *detect_unauthorized_peering(peering_resources, hub_ids),
        *detect_hub_bypass_routing(graph, hub_ids),
        *detect_segmentation_violations(graph, environments),
    ]

    findings = [
        Finding(audit_job_id=audit_job.id, module="validate", **raw)
        for raw in raw_findings
    ]
    db.add_all(findings)

    # Job status reflects execution health, not the number of findings -
    # a clean validation run that finds violations is still "completed".
    audit_job.status = "completed"
    db.commit()
    for finding in findings:
        db.refresh(finding)

    return findings


async def run_ai_validation(
    db: Session, audit_job: AuditJob, hub_vpc_ids: list[str], provider_name: str
) -> list[Finding]:
    """AI-based deviation detection (app/ai_engine/deviation_detector.py):
    an LLM reasons freely over the topology rather than following fixed
    rules. Probabilistic - results can vary between runs, unlike
    run_validation's deterministic rule engine. Offered as an alternative
    analysis mode the caller opts into, not a replacement.
    """
    audit_job.status = "validating"
    audit_job.hub_selection = {"hub_ids": hub_vpc_ids}
    db.commit()

    resources = _get_job_resources(db, audit_job.id)
    raw_findings = await detect_deviations_via_ai(provider_name, resources, hub_vpc_ids)

    findings = [
        Finding(audit_job_id=audit_job.id, module="ai_analysis", **raw)
        for raw in raw_findings
    ]
    db.add_all(findings)

    audit_job.status = "completed"
    db.commit()
    for finding in findings:
        db.refresh(finding)

    return findings


def list_findings(
    db: Session, audit_job_id: uuid.UUID, severity: str | None = None, finding_type: str | None = None
) -> list[Finding]:
    query = db.query(Finding).filter(Finding.audit_job_id == audit_job_id)
    if severity:
        query = query.filter(Finding.severity == severity)
    if finding_type:
        query = query.filter(Finding.finding_type == finding_type)
    return query.all()
