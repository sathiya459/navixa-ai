# ai_engine — NAVIXA InsightAI

Provider-agnostic LLM insight generation. All AI calls happen server-side only.

## Files

- `base.py` — abstract `AIProvider` interface.
- `registry.py` — provider registry under `providers/` (claude, openai, azure_openai, gemini, bedrock).
- `prompts.py` — prompt builders for root-cause analysis, recommendations, executive summaries, topology explanation.
- `service.py` — `generate_insights`.
- `deviation_detector.py` — AI-based deviation detection, invoked from `hub_spoke_validator/service.py`. `summarize_network_for_ai()` builds the prompt summary cross-provider using `graph_engine/attribute_extraction.py` for peering endpoints, owning network, route targets, and open-ingress signals.
- `topology_builder.py` — `summarize_topology_for_ai()`, used by `service.py`'s `topology_explanation` insight type. Narration-only: it summarizes the already-built NAVIXA Graph (node/edge counts by type, designated hub networks) for the prompt; the AI explains the shape in plain language but never proposes or infers the relationships themselves - deterministic code (`graph_engine/writer.py`) stays the sole source of truth for graph structure.

## Notes

Provider choice and API keys come from `config/settings.py`. The frontend never talks to AI providers directly — it only calls `api/v1/insightai.py`.
