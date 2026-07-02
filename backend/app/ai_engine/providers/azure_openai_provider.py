from openai import AsyncAzureOpenAI

from app.ai_engine.base import AIProvider, AIProviderError
from app.config.settings import get_settings

settings = get_settings()


class AzureOpenAIProvider(AIProvider):
    name = "azure_openai"

    def is_configured(self) -> bool:
        return bool(
            settings.azure_openai_api_key
            and settings.azure_openai_endpoint
            and settings.azure_openai_deployment
        )

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.is_configured():
            raise AIProviderError(
                "Azure OpenAI provider is not configured "
                "(AZURE_OPENAI_API_KEY / ENDPOINT / DEPLOYMENT missing)"
            )

        client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version="2024-08-01-preview",
        )
        response = await client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""
