"""Password hashing and signed access tokens for User and Access (FR-01, QR-04).

Passwords: PBKDF2-HMAC-SHA256 with a random 16-byte salt and 600000 iterations (the OWASP figure for
this algorithm). The stored text is `pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>`, so the
algorithm and cost travel with each hash and can be raised later without breaking old hashes.

Tokens: JWT signed with HS256 (PyJWT). Claims are `sub` (user id as a string, as the JWT standard
requires), `role` and `exp`.

This module does not import from app.core: it raises its own TokenError, and the auth service
translates it into AuthenticationFailed. That keeps the crypto code independent of the web layer.
"""

import base64
import binascii
import hashlib
import hmac
import logging
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

logger = logging.getLogger(__name__)

HASH_ALGORITHM = "pbkdf2_sha256"
HASH_ITERATIONS = 600_000
SALT_BYTES = 16

TOKEN_ALGORITHM = "HS256"
TOKEN_LIFETIME = timedelta(minutes=60)
_DEVELOPMENT_SECRET = "cfbs-development-secret-do-not-use-in-production"


class TokenError(Exception):
    """An access token is malformed, has a bad signature, or has expired."""


@dataclass(frozen=True)
class TokenData:
    """What a valid access token says about its holder."""

    user_id: int
    role: str


def _load_secret() -> str:
    """Read CFBS_SECRET; fall back to a development secret with one warning."""
    secret = os.environ.get("CFBS_SECRET")
    if secret:
        return secret
    logger.warning("CFBS_SECRET is not set; using the development secret (unsafe outside dev)")
    return _DEVELOPMENT_SECRET


SECRET_KEY = _load_secret()


def _derive(password: str, salt: bytes, iterations: int) -> bytes:
    """PBKDF2-HMAC-SHA256 of the password. Raises ValueError if iterations < 1."""
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


def _to_b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def hash_password(password: str) -> str:
    """Return a salted hash of the password in the stored-text format described above."""
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _derive(password, salt, HASH_ITERATIONS)
    return "$".join([HASH_ALGORITHM, str(HASH_ITERATIONS), _to_b64(salt), _to_b64(digest)])


def verify_password(password: str, stored_hash: str) -> bool:
    """True only if the password matches the stored hash.

    A malformed stored hash returns False instead of raising, so a corrupt row can never crash a
    login. Only ValueError and binascii.Error are caught: they are the errors that bad stored text
    can cause (bad iteration count, iterations < 1, invalid base64). compare_digest takes the same
    time whether or not the bytes match, so timing does not reveal how close a guess was.
    """
    parts = stored_hash.split("$")
    if len(parts) != 4:
        return False
    algorithm, iterations_text, salt_b64, hash_b64 = parts
    if algorithm != HASH_ALGORITHM:
        return False
    try:
        iterations = int(iterations_text)
        salt = base64.b64decode(salt_b64, validate=True)
        expected = base64.b64decode(hash_b64, validate=True)
        candidate = _derive(password, salt, iterations)
    except (ValueError, binascii.Error):
        return False
    return hmac.compare_digest(candidate, expected)


def create_access_token(user_id: int, role: str, expires_in: timedelta = TOKEN_LIFETIME) -> str:
    """Return a signed token for the user that expires after `expires_in`."""
    claims = {"sub": str(user_id), "role": str(role), "exp": datetime.now(UTC) + expires_in}
    return jwt.encode(claims, SECRET_KEY, algorithm=TOKEN_ALGORITHM)


def decode_access_token(token: str) -> TokenData:
    """Check the signature and expiry and return the token's data, or raise TokenError."""
    try:
        claims = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[TOKEN_ALGORITHM],
            options={"require": ["sub", "role", "exp"]},
        )
        user_id = int(claims["sub"])
    except (jwt.PyJWTError, ValueError) as exc:
        raise TokenError("Invalid or expired access token") from exc
    return TokenData(user_id=user_id, role=str(claims["role"]))
