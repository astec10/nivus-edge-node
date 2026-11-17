"""Single-node credential enrollment and replay-resistant node heartbeat registry."""

import hashlib
import json
import re
import secrets
import time
import uuid
from datetime import datetime, timezone

from database import get_db_connection

ENROLLMENT_TTL_SECONDS = 10 * 60
HEARTBEAT_INTERVAL_SECONDS = 30
ONLINE_TIMEOUT_SECONDS = 90
MAX_CAPABILITIES = 16
ALLOWED_CAPABILITIES = frozenset({
    "telemetry.cpu",
    "telemetry.memory",
    "telemetry.disk",
    "telemetry.host_battery",
    "telemetry.temperature",
    "telemetry.power_estimate",
})
_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,47}$")
_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")


class EnrollmentAuthenticationError(Exception):
    """Enrollment code is invalid, expired, or already consumed."""


class NodeAuthenticationError(Exception):
    """Node credential or session is invalid or revoked."""


class HeartbeatReplayError(Exception):
    """Heartbeat sequence is duplicated or older than the last accepted one."""


def _epoch(value=None) -> float:
    if value is None:
        return time.time()
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Use um horário com fuso horário.")
        return value.astimezone(timezone.utc).timestamp()
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Horário interno inválido.")
    return float(value)


def _iso(epoch: float | None) -> str | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(float(epoch), timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _validate_name(name: str) -> str:
    if not isinstance(name, str):
        raise ValueError("Informe o nome do nó.")
    clean_name = " ".join(name.split())
    if not _NAME_PATTERN.fullmatch(clean_name):
        raise ValueError("O nome do nó deve ter 1 a 48 caracteres alfanuméricos, espaços, ponto, hífen ou sublinhado.")
    return clean_name


def _validate_metadata(agent_version: str, schema_version: int, capabilities) -> tuple[str, int, list[str]]:
    if not isinstance(agent_version, str) or not _VERSION_PATTERN.fullmatch(agent_version):
        raise ValueError("Versão do agente inválida.")
    if type(schema_version) is not int or not 1 <= schema_version <= 100:
        raise ValueError("Versão de esquema inválida.")
    if not isinstance(capabilities, (list, tuple)) or len(capabilities) > MAX_CAPABILITIES:
        raise ValueError("Lista de capacidades inválida.")
    normalized = list(capabilities)
    if any(not isinstance(item, str) or item not in ALLOWED_CAPABILITIES for item in normalized):
        raise ValueError("A lista contém capacidade não permitida.")
    if len(set(normalized)) != len(normalized):
        raise ValueError("A lista de capacidades contém duplicatas.")
    return agent_version, schema_version, sorted(normalized)


def create_node_enrollment(now=None) -> dict:
    current = _epoch(now)
    enrollment_id = uuid.uuid4().hex
    code = secrets.token_urlsafe(32)
    expires_at = current + ENROLLMENT_TTL_SECONDS
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        # Keep expired/used one-time records bounded without deleting active nodes.
        conn.execute(
            "DELETE FROM node_enrollments WHERE expires_at < ? "
            "OR (consumed_at IS NOT NULL AND consumed_at < ?)",
            (current - 24 * 60 * 60, current - 24 * 60 * 60),
        )
        conn.execute(
            "INSERT INTO node_enrollments "
            "(enrollment_id, token_sha256, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (enrollment_id, _digest(code), current, expires_at),
        )
        conn.commit()
        return {
            "enrollment_id": enrollment_id,
            "code": code,
            "created_at": _iso(current),
            "expires_at": _iso(expires_at),
            "expires_in_seconds": ENROLLMENT_TTL_SECONDS,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def enroll_node(code: str, name: str, now=None) -> dict:
    current = _epoch(now)
    clean_name = _validate_name(name)
    if not isinstance(code, str) or not 40 <= len(code) <= 128:
        raise EnrollmentAuthenticationError()

    node_id = uuid.uuid4().hex
    token = secrets.token_urlsafe(32)
    session_id = secrets.token_urlsafe(32)
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        enrollment = conn.execute(
            "SELECT enrollment_id FROM node_enrollments "
            "WHERE token_sha256 = ? AND consumed_at IS NULL AND expires_at >= ?",
            (_digest(code), current),
        ).fetchone()
        if enrollment is None:
            conn.rollback()
            raise EnrollmentAuthenticationError()

        conn.execute(
            "INSERT INTO nodes "
            "(node_id, name, token_sha256, active, created_at, last_seen, "
            "session_sha256, last_sequence, capabilities_json) "
            "VALUES (?, ?, ?, 1, ?, NULL, ?, -1, '[]')",
            (node_id, clean_name, _digest(token), current, _digest(session_id)),
        )
        cursor = conn.execute(
            "UPDATE node_enrollments SET consumed_at = ? "
            "WHERE enrollment_id = ? AND consumed_at IS NULL",
            (current, enrollment["enrollment_id"]),
        )
        if cursor.rowcount != 1:
            conn.rollback()
            raise EnrollmentAuthenticationError()
        conn.commit()
        return {
            "node_id": node_id,
            "name": clean_name,
            "token": token,
            "session_id": session_id,
            "created_at": _iso(current),
            "heartbeat_interval_seconds": HEARTBEAT_INTERVAL_SECONDS,
            "online_timeout_seconds": ONLINE_TIMEOUT_SECONDS,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_node_session(node_token: str) -> dict:
    if not isinstance(node_token, str) or not 40 <= len(node_token) <= 128:
        raise NodeAuthenticationError()
    session_id = secrets.token_urlsafe(32)
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        node = conn.execute(
            "SELECT node_id FROM nodes WHERE token_sha256 = ? AND active = 1",
            (_digest(node_token),),
        ).fetchone()
        if node is None:
            conn.rollback()
            raise NodeAuthenticationError()
        conn.execute(
            "UPDATE nodes SET session_sha256 = ?, last_sequence = -1 WHERE node_id = ?",
            (_digest(session_id), node["node_id"]),
        )
        conn.commit()
        return {
            "node_id": node["node_id"],
            "session_id": session_id,
            "next_sequence": 0,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def process_node_heartbeat(
    node_token: str,
    session_id: str,
    sequence: int,
    agent_version: str,
    schema_version: int,
    capabilities,
    now=None,
) -> dict:
    current = _epoch(now)
    if not isinstance(node_token, str) or not 40 <= len(node_token) <= 128:
        raise NodeAuthenticationError()
    if not isinstance(session_id, str) or not 40 <= len(session_id) <= 128:
        raise NodeAuthenticationError()
    if type(sequence) is not int or not 0 <= sequence <= 2**63 - 1:
        raise ValueError("Sequência do heartbeat inválida.")
    agent_version, schema_version, normalized_capabilities = _validate_metadata(
        agent_version, schema_version, capabilities
    )

    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        node = conn.execute(
            "SELECT node_id, session_sha256, last_sequence FROM nodes "
            "WHERE token_sha256 = ? AND active = 1",
            (_digest(node_token),),
        ).fetchone()
        if node is None or node["session_sha256"] != _digest(session_id):
            conn.rollback()
            raise NodeAuthenticationError()
        if sequence <= int(node["last_sequence"]):
            conn.rollback()
            raise HeartbeatReplayError()

        conn.execute(
            "UPDATE nodes SET last_seen = ?, last_sequence = ?, agent_version = ?, "
            "schema_version = ?, capabilities_json = ? WHERE node_id = ? AND active = 1",
            (
                current,
                sequence,
                agent_version,
                schema_version,
                json.dumps(normalized_capabilities, separators=(",", ":")),
                node["node_id"],
            ),
        )
        conn.commit()
        return {
            "status": "ok",
            "node_id": node["node_id"],
            "received_at": _iso(current),
            "online_timeout_seconds": ONLINE_TIMEOUT_SECONDS,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_nodes(now=None) -> list[dict]:
    current = _epoch(now)
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT node_id, name, active, created_at, last_seen, revoked_at, "
            "agent_version, schema_version, capabilities_json "
            "FROM nodes ORDER BY created_at, node_id"
        ).fetchall()
        result = []
        for row in rows:
            active = bool(row["active"])
            last_seen = float(row["last_seen"]) if row["last_seen"] is not None else None
            age = max(0, int(current - last_seen)) if last_seen is not None else None
            if not active:
                state = "revoked"
            elif last_seen is not None and age <= ONLINE_TIMEOUT_SECONDS:
                state = "online"
            else:
                state = "offline"
            try:
                capabilities = json.loads(row["capabilities_json"] or "[]")
            except (TypeError, json.JSONDecodeError):
                capabilities = []
            result.append(
                {
                    "node_id": row["node_id"],
                    "name": row["name"],
                    "active": active,
                    "status": state,
                    "created_at": _iso(row["created_at"]),
                    "last_seen": _iso(last_seen),
                    "last_seen_seconds_ago": age,
                    "agent_version": row["agent_version"],
                    "schema_version": row["schema_version"],
                    "capabilities": capabilities,
                }
            )
        return result
    finally:
        conn.close()


def revoke_node(node_id: str, now=None) -> bool:
    current = _epoch(now)
    replacement_digest = _digest(secrets.token_urlsafe(32))
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "UPDATE nodes SET active = 0, revoked_at = ?, token_sha256 = ?, "
            "session_sha256 = NULL WHERE node_id = ? AND active = 1",
            (current, replacement_digest, node_id),
        )
        conn.commit()
        return cursor.rowcount == 1
    finally:
        conn.close()
