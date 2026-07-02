"""Prompt templates for each NAVIXA InsightAI use case (Section 15).

Kept separate from providers.py so that improving prompts never requires
touching provider implementations, and switching providers never requires
touching prompts.
"""

from app.models.finding import Finding

SYSTEM_PROMPT = (
    "You are NAVIXA InsightAI, the AI analysis engine for NAVIXA AI, a "
    "multi-cloud network architecture audit platform. You explain cloud "
    "network security findings clearly and concisely for a mixed audience "
    "of cloud engineers and security auditors. Be specific and actionable; "
    "avoid generic advice."
)


def build_root_cause_prompt(finding: Finding) -> tuple[str, str]:
    user_prompt = (
        f"Explain the likely root cause of this network architecture finding.\n\n"
        f"Finding type: {finding.finding_type}\n"
        f"Severity: {finding.severity}\n"
        f"Title: {finding.title}\n"
        f"Description: {finding.description}\n\n"
        "Explain in 2-4 sentences why this condition likely arose in the "
        "environment (e.g. common misconfigurations, missing guardrails, "
        "drift from intended architecture)."
    )
    return SYSTEM_PROMPT, user_prompt


def build_recommendation_prompt(finding: Finding) -> tuple[str, str]:
    user_prompt = (
        f"Recommend a remediation for this network architecture finding.\n\n"
        f"Finding type: {finding.finding_type}\n"
        f"Severity: {finding.severity}\n"
        f"Title: {finding.title}\n"
        f"Description: {finding.description}\n\n"
        "Give a concrete, step-by-step remediation plan (3-5 steps). Where "
        "relevant, name the specific cloud console action or CLI/IaC change."
    )
    return SYSTEM_PROMPT, user_prompt


def build_executive_summary_prompt(findings: list[Finding]) -> tuple[str, str]:
    severity_counts: dict[str, int] = {}
    for finding in findings:
        severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1

    findings_summary = "\n".join(
        f"- [{f.severity.upper()}] {f.finding_type}: {f.title}" for f in findings
    ) or "No findings were identified."

    user_prompt = (
        "Write an executive summary of this NAVIXA AI network architecture "
        "audit for a non-technical leadership audience.\n\n"
        f"Severity breakdown: {severity_counts}\n\n"
        f"Findings:\n{findings_summary}\n\n"
        "Summarize overall risk posture in 3-5 sentences, call out the "
        "highest-priority issue if any, and avoid technical jargon."
    )
    return SYSTEM_PROMPT, user_prompt


def build_topology_explanation_prompt(topology_summary: str) -> tuple[str, str]:
    user_prompt = (
        "Explain this network topology in plain language for someone "
        "reviewing the audit who is not deeply familiar with cloud "
        "networking.\n\n"
        f"Topology summary:\n{topology_summary}\n\n"
        "Describe the overall shape of the architecture (e.g. hub-and-spoke, "
        "flat, mesh) and any notable connectivity patterns in 3-5 sentences."
    )
    return SYSTEM_PROMPT, user_prompt
