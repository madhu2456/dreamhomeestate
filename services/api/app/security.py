"""Password hashing, session signing, and password-reset token utilities."""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from itsdangerous import URLSafeTimedSerializer
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

# --- Password hashing ---

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# --- Session token signing ---

def _get_session_signer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(
        settings.secret_key,
        salt="session-salt",
        signer_kwargs={"key_derivation": "hmac"},
    )


def sign_session_id(session_id: uuid.UUID) -> str:
    """Produce a signed token containing the session id."""
    return _get_session_signer().dumps(str(session_id))


def unsign_session_id(token: str, max_age: int | None = None) -> str | None:
    """Return the session id string from a signed token, or None if invalid/expired."""
    serializer = _get_session_signer()
    try:
        return serializer.loads(token, max_age=max_age)
    except Exception:
        return None


def hash_token(token: str) -> str:
    """Hash a token for DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()


# --- Password reset tokens ---

def _get_reset_signer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(
        settings.secret_key,
        salt="password-reset-salt",
        signer_kwargs={"key_derivation": "hmac"},
    )


def generate_password_reset_token(user_id: uuid.UUID) -> str:
    """Generate a short-lived token for password reset (default 1 hour expiry)."""
    return _get_reset_signer().dumps(str(user_id))


def verify_password_reset_token(token: str, max_age: int = 3600) -> str | None:
    """Return the user_id string from a reset token, or None if invalid/expired."""
    try:
        return _get_reset_signer().loads(token, max_age=max_age)
    except Exception:
        return None
