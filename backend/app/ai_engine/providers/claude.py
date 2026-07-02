from anthropic import AsyncAnthropic

from app.ai_engine.base import AIProvider, AIProviderError
from app.config.settings import get_settings

settings = get_settings()


class ClaudeProvider(AIProvider):
    name = "claude"

    def is_configured(self) -> bool:
        return bool(settings.anthropic_api_key)

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.is_configured():
            raise AIProviderError("Claude provider is not configured (ANTHROPIC_API_KEY missing)")

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text")
