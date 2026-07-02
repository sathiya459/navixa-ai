"""Encrypts delegated cloud-tenant SSO session data (MSAL token caches,
AWS SSO OIDC client registrations/tokens) before it touches the database.

The key itself never lives in code or `.env` - it's sourced from Key Vault
via settings.delegated_token_encryption_key, the same pattern already used
for jwt_secret_key etc. (app/config/settings.py:_SECRET_FIELD_MAP).
"""

from cryptography.fernet import Fernet, InvalidToken

from app.config.settings import get_settings


class TokenDecryptionError(Exception):
    """Raised when stored ciphertext can't be decrypted with the current key."""


def _get_fernet() -> Fernet:
    settings = get_settings()
    if not settings.delegated_token_encryption_key:
        raise RuntimeError(
            "DELEGATED_TOKEN_ENCRYPTION_KEY is not configured - cannot encrypt/decrypt "
            "delegated cloud tenant sessions"
        )
    return Fernet(settings.delegated_token_encryption_key.encode())


def encrypt(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise TokenDecryptionError("Stored token cache could not be decrypted") from exc
