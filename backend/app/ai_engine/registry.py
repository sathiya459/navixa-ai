from app.ai_engine.base import AIProvider, AIProviderError
from app.ai_engine.providers.azure_openai_provider import AzureOpenAIProvider
from app.ai_engine.providers.bedrock import BedrockProvider
from app.ai_engine.providers.claude import ClaudeProvider
from app.ai_engine.providers.gemini import GeminiProvider
from app.ai_engine.providers.openai_provider import OpenAIProvider

_PROVIDERS: dict[str, AIProvider] = {
    "claude": ClaudeProvider(),
    "openai": OpenAIProvider(),
    "azure_openai": AzureOpenAIProvider(),
    "gemini": GeminiProvider(),
    "bedrock": BedrockProvider(),
}


def get_provider(name: str) -> AIProvider:
    provider = _PROVIDERS.get(name)
    if provider is None:
        raise AIProviderError(f"Unknown AI provider: {name}")
    return provider


def list_providers() -> list[dict]:
    return [
        {"provider": name, "available": True, "configured": provider.is_configured()}
        for name, provider in _PROVIDERS.items()
    ]
