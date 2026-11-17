"""Short-lived, revocable browser/API sessions backed by SQLite."""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from database import get_db_connection
from security import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token


COOKIE_NAME = "nivus_session"
COOKIE_SECURE = os.environ.get("NIVUS_AUTH_COOKIE_SECURE", "true").strip().lower() not in {"0", "false", "no"}
SESSION_SCHEMA = """
CREATE TABLE IF NOT EXISTS auth_sessions (
    session_hash TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    revoked_at INTEGER,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_active
    ON auth_sessions(username, revoked_at, expires_at);
"""


def _session_hash(session_id: str) -> str:
    return hashlib.sha256(session_id.encode("utf-8")).hexdigest()


def issue_session(username: str, role: str, password_change_required: bool = False) -> str:
    now = datetime.now(timezone.utc)
    lifetime = 10 if password_change_required else ACCESS_TOKEN_EXPIRE_MINUTES
    expires_at = now + timedelta(minutes=lifetime)
    session_id = secrets.token_urlsafe(32)
    token = create_access_token(
        username, role, password_change_required, session_id=session_id,
        issued_at=now, expires_at=expires_at,
    )
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO auth_sessions (session_hash, username, expires_at) VALUES (?, ?, ?)",
            (_session_hash(session_id), username, int(expires_at.timestamp())),
        )
        conn.execute("DELETE FROM auth_sessions WHERE expires_at < ?", (int(now.timestamp()),))
        conn.commit()
    finally:
        conn.close()
    return token


def session_is_active(session_id: str, username: str) -> bool:
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM auth_sessions WHERE session_hash = ? AND username = ? "
            "AND revoked_at IS NULL AND expires_at >= ?",
            (_session_hash(session_id), username, int(datetime.now(timezone.utc).timestamp())),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def revoke_session(session_id: str) -> None:
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE auth_sessions SET revoked_at = ? WHERE session_hash = ? AND revoked_at IS NULL",
            (int(datetime.now(timezone.utc).timestamp()), _session_hash(session_id)),
        )
        conn.commit()
    finally:
        conn.close()


def revoke_user_sessions(username: str) -> None:
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE auth_sessions SET revoked_at = ? WHERE username = ? AND revoked_at IS NULL",
            (int(datetime.now(timezone.utc).timestamp()), username),
        )
        conn.commit()
    finally:
        conn.close()


def set_session_cookie(response, token: str, password_change_required: bool = False) -> None:
    response.set_cookie(
        COOKIE_NAME, token, max_age=600 if password_change_required else ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True, secure=COOKIE_SECURE, samesite="strict", path="/",
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/", secure=COOKIE_SECURE, httponly=True, samesite="strict")
