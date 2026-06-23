"""
Security utilities: password hashing and JWT creation/verification.

Required environment variables (set these before running the app):
    JWT_SECRET_KEY   - a long, random secret string. Generate one with:
                        python -c "import secrets; print(secrets.token_hex(32))"

If JWT_SECRET_KEY is not set, a random key is generated at process startup
as a fallback so the app doesn't crash in development. This means tokens
will stop validating every time the server restarts — fine for local dev,
NOT fine for production. Set the env var for any real deployment.
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

# ── Password hashing ──────────────────────────────────────────────────────────
# Using the `bcrypt` package directly rather than passlib's CryptContext:
# passlib 1.7.4's bcrypt backend version-detection is broken against
# bcrypt>=4.0 (raises on hash/verify). Calling bcrypt directly avoids it.
# bcrypt has a hard 72-byte input limit; passwords are truncated to that
# length before hashing, same behavior passlib would have applied.
_BCRYPT_MAX_BYTES = 72


def hash_password(plain_password: str) -> str:
    pw_bytes = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    hashed = bcrypt.hashpw(pw_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pw_bytes = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    try:
        return bcrypt.checkpw(pw_bytes, hashed_password.encode("utf-8"))
    except ValueError:
        # Malformed/legacy hash in DB — treat as non-matching rather than 500.
        return False


# ── JWT ────────────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("JWT_SECRET_KEY") or secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

if not os.getenv("JWT_SECRET_KEY"):
    print(
        "[auth.security] WARNING: JWT_SECRET_KEY is not set. Using a randomly "
        "generated key for this process only. All existing tokens will be "
        "invalidated on restart. Set JWT_SECRET_KEY in your environment "
        "before deploying."
    )


def create_access_token(
    user_id: int,
    email: Optional[str] = None,
    expires_minutes: Optional[int] = None,
) -> str:
    """Create a signed JWT. 'sub' holds the user_id as a string (JWT spec
    requires 'sub' to be a string); email is included as a convenience claim."""
    expire_delta = timedelta(minutes=expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES)
    expire_at = datetime.now(timezone.utc) + expire_delta

    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire_at,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT. Raises jose.JWTError (or subclasses, e.g.
    ExpiredSignatureError) on any failure — callers are expected to catch
    this and translate it into an HTTP 401.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "JWTError",
]