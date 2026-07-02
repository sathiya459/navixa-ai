"""Secret Manager abstraction (Section 7): "Use environment variables
during development" / "Use Secret Managers / Key Vaults in production".

Providers take their configuration via constructor arguments rather than
reaching for a global `settings` object, specifically so get_settings()
itself can call get_secret_provider() during startup (to override
sensitive fields with values fetched from the vault) without a circular
import / infinite-recursion risk - both modules would otherwise import
each other's module-level `settings = get_settings()` before either
finishes constructing.
"""

import os
from abc import ABC, abstractmethod


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
    def __init__(self, region: str):
        self._region = region

    def get_secret(self, name: str) -> str:
        import boto3
        from botocore.exceptions import ClientError

        client = boto3.client("secretsmanager", region_name=self._region)
        try:
            response = client.get_secret_value(SecretId=name)
        except ClientError as exc:
            raise SecretProviderError(f"Failed to fetch secret '{name}' from AWS Secrets Manager") from exc
        return response["SecretString"]


class AzureKeyVaultProvider(SecretProvider):
    def __init__(self, vault_url: str | None):
        self._vault_url = vault_url

    def get_secret(self, name: str) -> str:
        from azure.core.exceptions import AzureError
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        if not self._vault_url:
            raise SecretProviderError("AZURE_KEY_VAULT_URL is not configured")

        client = SecretClient(vault_url=self._vault_url, credential=DefaultAzureCredential())
        try:
            secret = client.get_secret(name)
        except AzureError as exc:
            raise SecretProviderError(f"Failed to fetch secret '{name}' from Azure Key Vault") from exc
        return secret.value


def build_secret_provider(
    provider_name: str, *, azure_key_vault_url: str | None = None, aws_region: str = "us-east-1"
) -> SecretProvider:
    if provider_name == "env":
        return EnvSecretProvider()
    if provider_name == "azure_key_vault":
        return AzureKeyVaultProvider(azure_key_vault_url)
    if provider_name == "aws_secrets_manager":
        return AWSSecretsManagerProvider(aws_region)
    raise SecretProviderError(f"Unknown secret provider: {provider_name}")


def get_secret_provider() -> SecretProvider:
    """General-purpose accessor for application code running after
    startup (get_settings() has already returned by then, so no
    recursion risk here)."""
    from app.config.settings import get_settings

    settings = get_settings()
    return build_secret_provider(
        settings.secret_provider,
        azure_key_vault_url=settings.azure_key_vault_url,
        aws_region=settings.aws_secrets_manager_region,
    )
