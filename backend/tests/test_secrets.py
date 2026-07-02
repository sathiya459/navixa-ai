import pytest

from app.config.secrets import (
    AWSSecretsManagerProvider,
    AzureKeyVaultProvider,
    EnvSecretProvider,
    SecretProviderError,
    get_secret_provider,
)


def test_env_provider_reads_environment_variable(monkeypatch):
    monkeypatch.setenv("NAVIXA_TEST_SECRET", "super-secret-value")
    provider = EnvSecretProvider()
    assert provider.get_secret("NAVIXA_TEST_SECRET") == "super-secret-value"


def test_env_provider_raises_when_missing():
    provider = EnvSecretProvider()
    with pytest.raises(SecretProviderError):
        provider.get_secret("NAVIXA_DEFINITELY_UNSET_SECRET")


def test_get_secret_provider_defaults_to_env(monkeypatch):
    from app.config import secrets as secrets_module

    monkeypatch.setattr(secrets_module.settings, "secret_provider", "env")
    get_secret_provider.cache_clear()
    provider = get_secret_provider()
    assert isinstance(provider, EnvSecretProvider)


def test_get_secret_provider_selects_aws(monkeypatch):
    from app.config import secrets as secrets_module

    monkeypatch.setattr(secrets_module.settings, "secret_provider", "aws_secrets_manager")
    get_secret_provider.cache_clear()
    provider = get_secret_provider()
    assert isinstance(provider, AWSSecretsManagerProvider)


def test_get_secret_provider_selects_azure(monkeypatch):
    from app.config import secrets as secrets_module

    monkeypatch.setattr(secrets_module.settings, "secret_provider", "azure_key_vault")
    get_secret_provider.cache_clear()
    provider = get_secret_provider()
    assert isinstance(provider, AzureKeyVaultProvider)


def test_get_secret_provider_raises_for_unknown_provider(monkeypatch):
    from app.config import secrets as secrets_module

    monkeypatch.setattr(secrets_module.settings, "secret_provider", "does-not-exist")
    get_secret_provider.cache_clear()
    with pytest.raises(SecretProviderError):
        get_secret_provider()
    get_secret_provider.cache_clear()
    monkeypatch.setattr(secrets_module.settings, "secret_provider", "env")


def test_azure_key_vault_provider_requires_vault_url(monkeypatch):
    from app.config import secrets as secrets_module

    monkeypatch.setattr(secrets_module.settings, "azure_key_vault_url", None)
    provider = AzureKeyVaultProvider()
    with pytest.raises(SecretProviderError):
        provider.get_secret("some-secret")
