import uuid

from sqlalchemy.orm import Session

from app.ai_engine.prompts import (
    build_executive_summary_prompt,
    build_recommendation_prompt,
    build_root_cause_prompt,
    build_topology_explanation_prompt,
)
from app.ai_engine.registry import get_provider
from app.models.ai_insight import AIInsight
from app.models.finding import Finding


async def generate_insights(
    db: Session,
    audit_job_id: uuid.UUID,
    provider_name: str,
    insight_types: list[str],
) -> list[AIInsight]:
    provider = get_provider(provider_name)
    findings = db.query(Finding).filter(Finding.audit_job_id == audit_job_id).all()

    insights: list[AIInsight] = []

    if "root_cause" in insight_types:
        for finding in findings:
            system, user = build_root_cause_prompt(finding)
            content = await provider.complete(system, user)
            insights.append(
                AIInsight(
                    audit_job_id=audit_job_id,
                    finding_id=finding.id,
                    insight_type="root_cause",
                    ai_provider=provider_name,
                    content=content,
                )
            )

    if "recommendation" in insight_types:
        for finding in findings:
            system, user = build_recommendation_prompt(finding)
            content = await provider.complete(system, user)
            insights.append(
                AIInsight(
                    audit_job_id=audit_job_id,
                    finding_id=finding.id,
                    insight_type="recommendation",
                    ai_provider=provider_name,
                    content=content,
                )
            )

    if "exec_summary" in insight_types:
        system, user = build_executive_summary_prompt(findings)
        content = await provider.complete(system, user)
        insights.append(
            AIInsight(
                audit_job_id=audit_job_id,
                finding_id=None,
                insight_type="exec_summary",
                ai_provider=provider_name,
                content=content,
            )
        )

    if "topology_explanation" in insight_types:
        # Summarized from findings rather than a live navixa_graph query,
        # since that would require a reachable Neo4j instance at request
        # time; sufficient context for a plain-language explanation without
        # that dependency.
        resource_type_counts: dict[str, int] = {}
        for finding in findings:
            resource_type_counts[finding.finding_type] = (
                resource_type_counts.get(finding.finding_type, 0) + 1
            )
        summary_text = ", ".join(f"{k}: {v}" for k, v in resource_type_counts.items()) or "no findings"
        system, user = build_topology_explanation_prompt(summary_text)
        content = await provider.complete(system, user)
        insights.append(
            AIInsight(
                audit_job_id=audit_job_id,
                finding_id=None,
                insight_type="topology_explanation",
                ai_provider=provider_name,
                content=content,
            )
        )

    db.add_all(insights)
    db.commit()
    for insight in insights:
        db.refresh(insight)

    return insights


def list_insights(
    db: Session,
    audit_job_id: uuid.UUID,
    insight_type: str | None = None,
    finding_id: uuid.UUID | None = None,
) -> list[AIInsight]:
    query = db.query(AIInsight).filter(AIInsight.audit_job_id == audit_job_id)
    if insight_type:
        query = query.filter(AIInsight.insight_type == insight_type)
    if finding_id:
        query = query.filter(AIInsight.finding_id == finding_id)
    return query.all()
