"""Fernet-based encryption service for OAuth tokens."""

from cryptography.fernet import Fernet
from fastapi import HTTPException, status

from app.config import get_settings

settings = get_settings()

_fernet = Fernet(settings.oauth_encryption_key.encode())


def encrypt_text(plain: str) -> str:
    """Encrypt a plaintext string and return the Fernet token."""
    return _fernet.encrypt(plain.encode()).decode()


def decrypt_text(cipher: str) -> str:
    """Decrypt a Fernet token back to the original plaintext string.

    Raises HTTPException(500) on any decryption failure (bad key, corrupted
    data, or invalid token).
    """
    try:
        return _fernet.decrypt(cipher.encode()).decode()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt credentials",
        ) from exc
