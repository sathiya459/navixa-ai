"""AI-based network architecture deviation detection.

Unlike NAVIXA Validate's deterministic rule engine (app/hub_spoke_validator/
rules.py), this asks a configured LLM provider to reason freely over the
discovered topology and flag deviations - including ones no explicit rule
checks for. It is inherently probabilistic: results can vary between runs
and the model can miss things or produce false positives. This is offered
as an alternative analysis mode, not a replacement for the rule engine -
the caller (POST /validate/jobs/{id}/run) chooses which one to run via
`analysis_mode`.
"""

import json
import re
from typing import Any

from app.ai_engine.registry import get_provider
from app.graph_engine.attribute_extraction import (
    extract_open_ingress,
    extract_owning_network_id,
    extract_peering_endpoints,
    extract_route_targets,
)
from app.models.network_resource import NetworkResource

_VALID_SEVERITIES = {"critical", "high", "medium", "low", "informational"}

_SYSTEM_PROMPT = (
    "You are NAVIXA InsightAI's network architecture deviation detector. "
    "You are given a summary of a cloud network's discovered resources and "
    "the account's designated Hub VPCs/VNets. Identify architectural "
    "deviations from Hub-and-Spoke best practices: unauthorized direct "
    "connectivity between spokes, internet exposure that bypasses the hub, "
    "inconsistent segmentation, overly permissive security rules, or any "
    "other structural risk you can identify from the data given - not "
    "limited to a fixed checklist.\n\n"
    "Respond with ONLY a JSON array (no markdown fences, no prose before or "
    "after) of finding objects, each with exactly these keys:\n"
    '  "finding_type": short snake_case identifier\n'
    '  "severity": one of critical | high | medium | low | informational\n'
    '  "title": one-line summary\n'
    '  "description": 2-4 sentences explaining the deviation and why it matters\n'
    '  "affected_resource_ids": array of native resource IDs from the input\n\n'
    "If you find no deviations, respond with an empty JSON array: []"
)


def summarize_network_for_ai(resources: list[NetworkResource], hub_ids: list[str]) -> str:
    """Builds a compact plain-text description of the topology for the
    prompt - full raw attributes would be too large/noisy for most models'
    context windows and would bury the structurally relevant fields.
    """
    hub_id_set = set(hub_ids)
    lines: list[str] = []

    networks = [r for r in resources if r.resource_type == "network"]
    lines.append(f"Networks ({len(networks)}):")
    for network in networks:
        role = "HUB" if network.native_id in hub_id_set else "spoke"
        lines.append(f"  - {network.native_id} [{role}] name={network.name}")

    peerings = [r for r in resources if r.resource_type == "peering_connection"]
    lines.append(f"\nPeering connections ({len(peerings)}):")
    for peering in peerings:
        source_id, target_id = extract_peering_endpoints(peering.provider, peering.attributes)
        lines.append(f"  - {peering.native_id}: {source_id or '?'} <-> {target_id or '?'}")

    gateways = [r for r in resources if r.resource_type == "gateway"]
    lines.append(f"\nGateways ({len(gateways)}):")
    for gateway in gateways:
        gw_type = gateway.attributes.get("GatewayType", "unknown")
        lines.append(f"  - {gateway.native_id} type={gw_type}")

    route_tables = [r for r in resources if r.resource_type == "route_table"]
    lines.append(f"\nRoute tables ({len(route_tables)}):")
    for rt in route_tables:
        vpc_id = extract_owning_network_id(rt.provider, rt.attributes) or "?"
        targets = extract_route_targets(rt.provider, rt.attributes)
        lines.append(f"  - {rt.native_id} (vpc={vpc_id}) routes -> {targets}")

    security_groups = [r for r in resources if r.resource_type == "security_group"]
    lines.append(f"\nSecurity groups ({len(security_groups)}):")
    for sg in security_groups:
        open_ingress = extract_open_ingress(sg.provider, sg.attributes)
        vpc_id = extract_owning_network_id(sg.provider, sg.attributes) or "?"
        lines.append(
            f"  - {sg.native_id} (vpc={vpc_id}) open_ingress_from_internet={open_ingress}"
        )

    return "\n".join(lines)


def build_deviation_analysis_prompt(network_summary: str) -> tuple[str, str]:
    user_prompt = (
        "Analyze this network for Hub-and-Spoke architecture deviations:\n\n"
        f"{network_summary}"
    )
    return _SYSTEM_PROMPT, user_prompt


def parse_deviation_response(raw_text: str) -> list[dict[str, Any]]:
    """Parses the LLM's JSON response defensively: strips markdown code
    fences some models add despite instructions not to, and drops any
    entry missing a required field rather than failing the whole batch.
    """
    text = raw_text.strip()
    fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []

    if not isinstance(parsed, list):
        return []

    findings = []
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        if not all(k in entry for k in ("finding_type", "severity", "title", "description")):
            continue
        severity = entry["severity"] if entry["severity"] in _VALID_SEVERITIES else "medium"
        findings.append(
            {
                "finding_type": str(entry["finding_type"]),
                "severity": severity,
                "title": str(entry["title"]),
                "description": str(entry["description"]),
                "affected_resource_ids": [str(r) for r in entry.get("affected_resource_ids", [])],
            }
        )

    return findings


async def detect_deviations_via_ai(
    provider_name: str, resources: list[NetworkResource], hub_ids: list[str]
) -> list[dict[str, Any]]:
    provider = get_provider(provider_name)
    summary = summarize_network_for_ai(resources, hub_ids)
    system_prompt, user_prompt = build_deviation_analysis_prompt(summary)
    raw_response = await provider.complete(system_prompt, user_prompt)
    return parse_deviation_response(raw_response)
