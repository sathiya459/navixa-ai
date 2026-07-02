import pytest
from cryptography.fernet import Fernet

from app.auth.token_encryption import TokenDecryptionError, decrypt, encrypt


def test_encrypt_decrypt_round_trip(monkeypatch):
    from app.config import settings as settings_module

    settings = settings_module.get_settings()
    monkeypatch.setattr(settings, "delegated_token_encryption_key", Fernet.generate_key().decode())

    ciphertext = encrypt("super-secret-token-cache")
    assert ciphertext != "super-secret-token-cache"
    assert decrypt(ciphertext) == "super-secret-token-cache"


def test_decrypt_raises_on_tampered_ciphertext(monkeypatch):
    from app.config import settings as settings_module

    settings = settings_module.get_settings()
    monkeypatch.setattr(settings, "delegated_token_encryption_key", Fernet.generate_key().decode())

    ciphertext = encrypt("some-value")
    with pytest.raises(TokenDecryptionError):
        decrypt(ciphertext[:-2] + "xx")


def test_decrypt_fails_with_wrong_key(monkeypatch):
    from app.config import settings as settings_module

    settings = settings_module.get_settings()
    monkeypatch.setattr(settings, "delegated_token_encryption_key", Fernet.generate_key().decode())
    ciphertext = encrypt("some-value")

    monkeypatch.setattr(settings, "delegated_token_encryption_key", Fernet.generate_key().decode())
    with pytest.raises(TokenDecryptionError):
        decrypt(ciphertext)
