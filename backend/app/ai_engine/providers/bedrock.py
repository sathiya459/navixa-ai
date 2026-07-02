import json

import aioboto3

from app.ai_engine.base import AIProvider, AIProviderError
from app.config.settings import get_settings

settings = get_settings()


class BedrockProvider(AIProvider):
    name = "bedrock"

    def is_configured(self) -> bool:
        # Bedrock uses the platform's AWS credential chain (Section 8: IAM
        # Identity Center / AssumeRole), not a standalone API key, so
        # "configured" just means a model + region are set.
        return bool(settings.aws_bedrock_model_id and settings.aws_default_region)

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.is_configured():
            raise AIProviderError("Bedrock provider is not configured (model/region missing)")

        session = aioboto3.Session()
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            }
        )

        async with session.client("bedrock-runtime", region_name=settings.aws_default_region) as client:
            response = await client.invoke_model(modelId=settings.aws_bedrock_model_id, body=body)
            payload = json.loads(await response["body"].read())
            return "".join(block["text"] for block in payload.get("content", []) if block.get("type") == "text")
