import asyncio

import google.generativeai as genai

from app.ai_engine.base import AIProvider, AIProviderError
from app.config.settings import get_settings

settings = get_settings()


class GeminiProvider(AIProvider):
    """The google-generativeai SDK is synchronous only, so calls run via
    asyncio.to_thread (same pattern as the GCP/OCI collectors)."""

    name = "gemini"

    def is_configured(self) -> bool:
        return bool(settings.gemini_api_key)

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.is_configured():
            raise AIProviderError("Gemini provider is not configured (GEMINI_API_KEY missing)")

        def _call() -> str:
            genai.configure(api_key=settings.gemini_api_key)
            model = genai.GenerativeModel(settings.gemini_model, system_instruction=system_prompt)
            response = model.generate_content(user_prompt)
            return response.text

        return await asyncio.to_thread(_call)
