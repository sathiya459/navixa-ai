# ai_engine — NAVIXA InsightAI

Provider-agnostic LLM insight generation. All AI calls happen server-side only.

## Files

- `base.py` — abstract `AIProvider` interface.
- `registry.py` — provider registry under `providers/` (claude, openai, azure_openai, gemini, bedrock).
- `prompts.py` — prompt builders for root-cause analysis, recommendations, executive summaries, topology explanation.
- `service.py` — `generate_insights`.
- `deviation_detector.py` — AI-based deviation detection, invoked from `hub_spoke_validator/service.py`.

## Notes

Provider choice and API keys come from `config/settings.py`. The frontend never talks to AI providers directly — it only calls `api/v1/insightai.py`.
