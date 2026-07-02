import uuid
from typing import Literal

from sqlalchemy.orm import Session

from app.hub_spoke_validator.graph_builder import build_network_graph
from app.internet_path_engine.analyzer import analyze_egress_exposure, analyze_ingress_exposure
from app.models.audit_job import AuditJob, AuditJobScope
from app.models.finding import Finding
from app.models.network_resource import NetworkResource

Direction = Literal["ingress", "egress", "both"]


def run_pathfinder(db: Session, audit_job: AuditJob, direction: Direction) -> list[Finding]:
    audit_job.status = "pathfinding"
    db.commit()

    resources = (
        db.query(NetworkResource)
        .join(AuditJobScope, NetworkResource.audit_job_scope_id == AuditJobScope.id)
        .filter(AuditJobScope.audit_job_id == audit_job.id)
        .all()
    )
    graph = build_network_graph(resources)

    raw_findings = []
    if direction in ("ingress", "both"):
        raw_findings.extend(analyze_ingress_exposure(graph, resources))
    if direction in ("egress", "both"):
        raw_findings.extend(analyze_egress_exposure(graph, resources))

    findings = [
        Finding(audit_job_id=audit_job.id, module="pathfinder", **raw) for raw in raw_findings
    ]
    db.add_all(findings)

    audit_job.status = "completed"
    db.commit()
    for finding in findings:
        db.refresh(finding)

    return findings


def list_pathfinder_findings(
    db: Session, audit_job_id: uuid.UUID, finding_type: str | None = None
) -> list[Finding]:
    query = db.query(Finding).filter(
        Finding.audit_job_id == audit_job_id, Finding.module == "pathfinder"
    )
    if finding_type:
        query = query.filter(Finding.finding_type == finding_type)
    return query.all()
