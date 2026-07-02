from openai import AsyncOpenAI

from app.ai_engine.base import AIProvider, AIProviderError
from app.config.settings import get_settings

settings = get_settings()


class OpenAIProvider(AIProvider):
    name = "openai"

    def is_configured(self) -> bool:
        return bool(settings.openai_api_key)

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.is_configured():
            raise AIProviderError("OpenAI provider is not configured (OPENAI_API_KEY missing)")

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""
