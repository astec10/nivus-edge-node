"""Password hashing and JWT helpers for the live Nivus API."""

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
PBKDF2_ITERATIONS = 600_000
PASSWORD_SCHEME = "pbkdf2_sha256"
DEFAULT_CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
DEFAULT_JWT_SECRET_FILE = DEFAULT_CONFIG_DIR / "nivus-edge" / "jwt_secret"
JWT_SECRET_FILE = Path(
    os.environ.get("NIVUS_JWT_SECRET_FILE", str(DEFAULT_JWT_SECRET_FILE))
)


def load_jwt_secret() -> str:
    try:
        secret = JWT_SECRET_FILE.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(f"JWT secret file is unavailable: {JWT_SECRET_FILE}") from exc
    if len(secret) < 64:
        raise RuntimeError("JWT secret must contain at least 64 characters")
    return secret


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS, dklen=32
    )
    return "$".join(
        (PASSWORD_SCHEME, str(PBKDF2_ITERATIONS), _b64encode(salt), _b64encode(digest))
    )


def is_password_hash(encoded: str) -> bool:
    return encoded.startswith(f"{PASSWORD_SCHEME}$")


def verify_password(password: str, stored: str) -> bool:
    if not is_password_hash(stored):
        return hmac.compare_digest(password.encode("utf-8"), stored.encode("utf-8"))
    try:
        scheme, iteration_text, salt_text, digest_text = stored.split("$", 3)
        iterations = int(iteration_text)
        if scheme != PASSWORD_SCHEME or not 100_000 <= iterations <= 2_000_000:
            return False
        salt = _b64decode(salt_text)
        expected = _b64decode(digest_text)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations, dklen=len(expected)
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(username: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, load_jwt_secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, load_jwt_secret(), algorithms=[ALGORITHM])
