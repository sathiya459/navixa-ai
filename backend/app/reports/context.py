"""Builds the data context shared by all three NAVIXA Reports renderers
(HTML/PDF/Excel), so report content stays consistent across formats."""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models.ai_insight import AIInsight
from app.models.audit_job import AuditJob
from app.models.cloud_tenant import CloudTenant
from app.models.finding import Finding


@dataclass
class ReportContext:
    audit_job_id: str
    tenant_name: str
    provider: str
    job_status: str
    created_at: str
    findings: list[dict[str, Any]]
    severity_counts: dict[str, int]
    exec_summary: str | None
    generated_at: str = field(default="")


def build_report_context(db: Session, audit_job: AuditJob) -> ReportContext:
    tenant = db.get(CloudTenant, audit_job.tenant_id)
    findings = db.query(Finding).filter(Finding.audit_job_id == audit_job.id).all()

    severity_counts: dict[str, int] = {}
    for finding in findings:
        severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1

    exec_summary_insight = (
        db.query(AIInsight)
        .filter(AIInsight.audit_job_id == audit_job.id, AIInsight.insight_type == "exec_summary")
        .order_by(AIInsight.created_at.desc())
        .first()
    )

    return ReportContext(
        audit_job_id=str(audit_job.id),
        tenant_name=tenant.tenant_name if tenant else "Unknown",
        provider=tenant.provider if tenant else "unknown",
        job_status=audit_job.status,
        created_at=audit_job.created_at.isoformat(),
        findings=[
            {
                "id": str(f.id),
                "module": f.module,
                "finding_type": f.finding_type,
                "severity": f.severity,
                "title": f.title,
                "description": f.description,
                "status": f.status,
            }
            for f in findings
        ],
        severity_counts=severity_counts,
        exec_summary=exec_summary_insight.content if exec_summary_insight else None,
    )
