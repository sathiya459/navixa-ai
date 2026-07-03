# hub_spoke_validator — NAVIXA Validate

Deterministic hub-and-spoke compliance rule engine, plus AI-assisted deviation detection.

## Files

- `graph_builder.py` — builds an in-memory NetworkX graph from job inventory (AWS-shaped edges).
- `rules.py` — deterministic checks: `unauthorized_peering`, `hub_bypass_routing`, `segmentation_violation`.
- `service.py` — `run_validation` orchestrates the analysis; also invokes `ai_engine.deviation_detector` for AI-based findings.

## Notes

Rule checks are same-input-same-output and produce auditable `Finding` rows — this is intentionally kept separate from the AI-based deviation detection in `ai_engine/`, which augments but doesn't replace the deterministic rules.
