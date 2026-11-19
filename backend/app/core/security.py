"""Password hashing, access tokens and password-reset tokens."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from backend.app.core.config import settings

ALGORITHM = "HS256"  # pinned: tokens signed with any other algorithm are rejected
_hasher = PasswordHasher()  # Argon2id
_DUMMY_HASH = _hasher.hash("timing-equaliser-not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """Verify Argon2id hashes, and bcrypt hashes created by the previous version.

    Passing ``None`` still performs a full hash so that a login for an unknown
    email takes as long as one for a real account.
    """
    if hashed_password is None:
        _safe_argon2_verify(_DUMMY_HASH, plain_password)
        return False
    if hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            return bcrypt.checkpw(plain_password.encode()[:72], hashed_password.encode())
        except ValueError:
            return False
    return _safe_argon2_verify(hashed_password, plain_password)


def _safe_argon2_verify(hashed: str, plain: str) -> bool:
    try:
        return _hasher.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(hashed_password: str) -> bool:
    """True for legacy bcrypt hashes and Argon2 hashes with outdated parameters."""
    if not hashed_password.startswith("$argon2"):
        return True
    return _hasher.check_needs_rehash(hashed_password)


def create_access_token(subject: int | str) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": str(subject),
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "iss": settings.PROJECT_NAME,
        "jti": uuid.uuid4().hex,
        "typ": "access",
    }
    return jwt.encode(claims, settings.SECRET_KEY.get_secret_value(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[ALGORITHM],
            issuer=settings.PROJECT_NAME,
            options={"require": ["sub", "exp", "iat", "iss", "typ"]},
        )
    except jwt.PyJWTError as exc:
        raise ValueError("Invalid or expired token") from exc
    if payload.get("typ") != "access":
        raise ValueError("Invalid or expired token")
    return payload


def create_password_reset_token() -> tuple[str, str]:
    """Return (token for the email link, SHA-256 hash to store in the database)."""
    token = secrets.token_urlsafe(32)
    return token, hash_reset_token(token)


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
