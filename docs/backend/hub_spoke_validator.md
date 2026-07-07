# hub_spoke_validator — NAVIXA Validate

Deterministic hub-and-spoke compliance rule engine, plus AI-assisted deviation detection.

## Files

- `graph_builder.py` — builds an in-memory NetworkX graph from job inventory. `PEERED_WITH` edges are cross-provider (via `graph_engine/attribute_extraction.py`); `ATTACHED_TO`/`ROUTES_TO` edges remain AWS-shaped.
- `rules.py` — deterministic checks: `unauthorized_peering`, `hub_bypass_routing`, `segmentation_violation`.
- `service.py` — `run_validation` orchestrates the analysis; also invokes `ai_engine.deviation_detector` for AI-based findings.

## Notes

Rule checks are same-input-same-output and produce auditable `Finding` rows — this is intentionally kept separate from the AI-based deviation detection in `ai_engine/`, which augments but doesn't replace the deterministic rules.

`detect_unauthorized_peering` and the `PEERED_WITH` edges feeding `detect_segmentation_violations` work across AWS/Azure/GCP via `graph_engine/attribute_extraction.py::extract_peering_endpoints`. `hub_bypass_routing` (via `ATTACHED_TO`/`ROUTES_TO` edges) is still AWS-only — deriving gateway/route ownership reliably for other providers needs deeper provider-specific routing-model heuristics, which risks wrong findings in a security tool, so it's left as a known gap rather than guessed.
