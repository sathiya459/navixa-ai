"""Secret Manager abstraction (Section 7): "Use environment variables
during development" / "Use Secret Managers / Key Vaults in production".

This is a utility other modules can opt into for secrets that need
runtime rotation or centralized audit (e.g. re-fetching a rotated API key
without redeploying) - it does not replace pydantic-settings' env-var
loading for static configuration, which remains the primary mechanism for
values fixed at deploy time. Selection is driven by `settings.secret_provider`.
"""

import os
from abc import ABC, abstractmethod
from functools import lru_cache

from app.config.settings import get_settings

settings = get_settings()


class SecretProviderError(RuntimeError):
    """Raised when a secret cannot be resolved."""


class SecretProvider(ABC):
    @abstractmethod
    def get_secret(self, name: str) -> str:
        """Returns the current value of the named secret, or raises
        SecretProviderError if it cannot be resolved."""


class EnvSecretProvider(SecretProvider):
    """Development default: reads secrets directly from the process
    environment (populated via .env in dev, real env vars in prod without
    a dedicated Secret Manager)."""

    def get_secret(self, name: str) -> str:
        value = os.environ.get(name)
        if value is None:
            raise SecretProviderError(f"Secret '{name}' is not set in the environment")
        return value


class AWSSecretsManagerProvider(SecretProvider):
    def get_secret(self, name: str) -> str:
        import boto3
        from botocore.exceptions import ClientError

        client = boto3.client("secretsmanager", region_name=settings.aws_secrets_manager_region)
        try:
            response = client.get_secret_value(SecretId=name)
        except ClientError as exc:
            raise SecretProviderError(f"Failed to fetch secret '{name}' from AWS Secrets Manager") from exc
        return response["SecretString"]


class AzureKeyVaultProvider(SecretProvider):
    def get_secret(self, name: str) -> str:
        from azure.core.exceptions import AzureError
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        if not settings.azure_key_vault_url:
            raise SecretProviderError("AZURE_KEY_VAULT_URL is not configured")

        client = SecretClient(vault_url=settings.azure_key_vault_url, credential=DefaultAzureCredential())
        try:
            secret = client.get_secret(name)
        except AzureError as exc:
            raise SecretProviderError(f"Failed to fetch secret '{name}' from Azure Key Vault") from exc
        return secret.value


_PROVIDERS: dict[str, type[SecretProvider]] = {
    "env": EnvSecretProvider,
    "aws_secrets_manager": AWSSecretsManagerProvider,
    "azure_key_vault": AzureKeyVaultProvider,
}


@lru_cache
def get_secret_provider() -> SecretProvider:
    provider_cls = _PROVIDERS.get(settings.secret_provider)
    if provider_cls is None:
        raise SecretProviderError(f"Unknown secret provider: {settings.secret_provider}")
    return provider_cls()
