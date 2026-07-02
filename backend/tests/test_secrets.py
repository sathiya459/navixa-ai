import pytest

from app.config.secrets import (
    AWSSecretsManagerProvider,
    AzureKeyVaultProvider,
    EnvSecretProvider,
    SecretProviderError,
    build_secret_provider,
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


def test_build_secret_provider_defaults_to_env():
    assert isinstance(build_secret_provider("env"), EnvSecretProvider)


def test_build_secret_provider_selects_aws():
    provider = build_secret_provider("aws_secrets_manager", aws_region="eu-west-1")
    assert isinstance(provider, AWSSecretsManagerProvider)
    assert provider._region == "eu-west-1"


def test_build_secret_provider_selects_azure():
    provider = build_secret_provider("azure_key_vault", azure_key_vault_url="https://vault.example/")
    assert isinstance(provider, AzureKeyVaultProvider)
    assert provider._vault_url == "https://vault.example/"


def test_build_secret_provider_raises_for_unknown_provider():
    with pytest.raises(SecretProviderError):
        build_secret_provider("does-not-exist")


def test_azure_key_vault_provider_requires_vault_url():
    provider = AzureKeyVaultProvider(vault_url=None)
    with pytest.raises(SecretProviderError):
        provider.get_secret("some-secret")


def test_get_secret_provider_reflects_current_settings(monkeypatch):
    from app.config.settings import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "secret_provider", "env")
    assert isinstance(get_secret_provider(), EnvSecretProvider)
