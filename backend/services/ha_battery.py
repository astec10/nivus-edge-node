"""Least-privilege Home Assistant discovery bridge for mobile battery sensors."""

import hashlib
import secrets
import time
import uuid
from datetime import datetime, timezone

from database import get_db_connection
from services.mobile_battery import process_mobile_battery_device_report

PAIRING_TTL_SECONDS = 10 * 60
MAX_DISCOVERY_CANDIDATES = 200


class HomeAssistantBridgeAuthenticationError(Exception):
    """The bridge credential or pairing code is invalid or revoked."""


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _iso_timestamp(value):
    if value is None:
        return None
    return datetime.fromtimestamp(float(value), timezone.utc).isoformat(timespec="seconds")


def create_pairing(created_by: str, now: float | None = None) -> dict:
    current = time.time() if now is None else float(now)
    pairing_id = uuid.uuid4().hex
    pairing_code = secrets.token_urlsafe(32)
    expires_at = current + PAIRING_TTL_SECONDS
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO mobile_battery_ha_pairings "
            "(pairing_id, code_sha256, created_by, created_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (pairing_id, _digest(pairing_code), created_by, current, expires_at),
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "pairing_id": pairing_id,
        "pairing_code": pairing_code,
        "expires_at": datetime.fromtimestamp(expires_at, timezone.utc).isoformat(timespec="seconds"),
    }


def consume_pairing(pairing_code: str, name: str, now: float | None = None) -> dict:
    if not isinstance(pairing_code, str) or not 40 <= len(pairing_code) <= 64:
        raise HomeAssistantBridgeAuthenticationError()
    clean_name = " ".join(str(name).split())[:80] or "Home Assistant"
    current = time.time() if now is None else float(now)
    connection_id = uuid.uuid4().hex
    bridge_token = secrets.token_urlsafe(48)
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        pairing = conn.execute(
            "SELECT pairing_id, expires_at, consumed_at FROM mobile_battery_ha_pairings "
            "WHERE code_sha256 = ?",
            (_digest(pairing_code),),
        ).fetchone()
        if pairing is None or pairing["consumed_at"] is not None or float(pairing["expires_at"]) <= current:
            conn.rollback()
            raise HomeAssistantBridgeAuthenticationError()
        conn.execute(
            "INSERT INTO mobile_battery_ha_connections "
            "(connection_id, name, token_sha256, created_at, last_seen_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (connection_id, clean_name, _digest(bridge_token), current, current),
        )
        conn.execute(
            "UPDATE mobile_battery_ha_pairings SET consumed_at = ? WHERE pairing_id = ?",
            (current, pairing["pairing_id"]),
        )
        conn.commit()
        return {"connection_id": connection_id, "name": clean_name, "bridge_token": bridge_token}
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


def _get_connection(conn, bridge_token: str):
    if not isinstance(bridge_token, str) or not 40 <= len(bridge_token) <= 128:
        raise HomeAssistantBridgeAuthenticationError()
    row = conn.execute(
        "SELECT connection_id, name FROM mobile_battery_ha_connections "
        "WHERE token_sha256 = ? AND active = 1",
        (_digest(bridge_token),),
    ).fetchone()
    if row is None:
        raise HomeAssistantBridgeAuthenticationError()
    return row


def discover_candidates(bridge_token: str, candidates: list[dict], now: float | None = None) -> dict:
    if len(candidates) > MAX_DISCOVERY_CANDIDATES:
        raise ValueError("O Home Assistant enviou candidatos demais.")
    current = time.time() if now is None else float(now)
    conn = get_db_connection()
    try:
        bridge = _get_connection(conn, bridge_token)
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "UPDATE mobile_battery_ha_connections SET last_seen_at = ? WHERE connection_id = ? AND active = 1",
            (current, bridge["connection_id"]),
        )
        for candidate in candidates:
            conn.execute(
                "INSERT INTO mobile_battery_ha_candidates "
                "(candidate_id, connection_id, entity_id, device_name, manufacturer, model, last_discovered_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(connection_id, entity_id) DO UPDATE SET "
                "device_name = excluded.device_name, manufacturer = excluded.manufacturer, "
                "model = excluded.model, last_discovered_at = excluded.last_discovered_at",
                (
                    uuid.uuid4().hex,
                    bridge["connection_id"],
                    candidate["entity_id"],
                    candidate["device_name"],
                    candidate.get("manufacturer"),
                    candidate.get("model"),
                    current,
                ),
            )
        conn.commit()
        return {"status": "discovered", "count": len(candidates)}
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


def list_connections() -> list[dict]:
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT connection_id, name, active, created_at, last_seen_at "
            "FROM mobile_battery_ha_connections ORDER BY created_at, connection_id"
        ).fetchall()
        return [
            {
                "connection_id": row["connection_id"],
                "name": row["name"],
                "active": bool(row["active"]),
                "created_at": _iso_timestamp(row["created_at"]),
                "last_seen_at": _iso_timestamp(row["last_seen_at"]),
            }
            for row in rows
        ]
    finally:
        conn.close()


def list_candidates() -> list[dict]:
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT c.candidate_id, c.connection_id, h.name AS connection_name, h.active AS connection_active, "
            "c.entity_id, c.device_name, c.manufacturer, c.model, c.selected, c.last_discovered_at, "
            "d.last_battery_percent, d.last_observed_at "
            "FROM mobile_battery_ha_candidates c "
            "JOIN mobile_battery_ha_connections h ON h.connection_id = c.connection_id "
            "LEFT JOIN mobile_battery_devices d ON d.device_id = c.mobile_battery_device_id "
            "ORDER BY c.device_name, c.entity_id"
        ).fetchall()
        return [
            {
                "candidate_id": row["candidate_id"],
                "connection_id": row["connection_id"],
                "connection_name": row["connection_name"],
                "connection_active": bool(row["connection_active"]),
                "entity_id": row["entity_id"],
                "device_name": row["device_name"],
                "manufacturer": row["manufacturer"],
                "model": row["model"],
                "selected": bool(row["selected"]),
                "last_discovered_at": _iso_timestamp(row["last_discovered_at"]),
                "last_battery_percent": row["last_battery_percent"],
                "last_observed_at": _iso_timestamp(row["last_observed_at"]),
            }
            for row in rows
        ]
    finally:
        conn.close()


def set_candidate_selected(candidate_id: str, selected: bool, now: float | None = None) -> dict | None:
    current = time.time() if now is None else float(now)
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        candidate = conn.execute(
            "SELECT candidate_id, device_name, entity_id, selected, mobile_battery_device_id "
            "FROM mobile_battery_ha_candidates c "
            "JOIN mobile_battery_ha_connections h ON h.connection_id = c.connection_id "
            "WHERE c.candidate_id = ? AND h.active = 1",
            (candidate_id,),
        ).fetchone()
        if candidate is None:
            conn.rollback()
            return None
        device_id = candidate["mobile_battery_device_id"]
        if selected and device_id is None:
            device_id = uuid.uuid4().hex
            internal_token_digest = _digest(secrets.token_urlsafe(32))
            safe_name = candidate["device_name"][:48]
            conn.execute(
                "INSERT INTO mobile_battery_devices "
                "(device_id, name, token_sha256, active, source_type, source_ref) "
                "VALUES (?, ?, ?, 1, 'home_assistant', ?)",
                (device_id, safe_name, internal_token_digest, candidate_id),
            )
        if device_id is not None:
            conn.execute(
                "UPDATE mobile_battery_devices SET active = ? WHERE device_id = ?",
                (int(bool(selected)), device_id),
            )
        conn.execute(
            "UPDATE mobile_battery_ha_candidates SET selected = ?, mobile_battery_device_id = ? "
            "WHERE candidate_id = ?",
            (int(bool(selected)), device_id, candidate_id),
        )
        conn.execute(
            "UPDATE mobile_battery_ha_connections SET last_seen_at = ? "
            "WHERE connection_id = (SELECT connection_id FROM mobile_battery_ha_candidates WHERE candidate_id = ?)",
            (current, candidate_id),
        )
        conn.commit()
        return {
            "candidate_id": candidate_id,
            "selected": bool(selected),
            "device_id": device_id,
        }
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


def get_selected_candidates(bridge_token: str, now: float | None = None) -> list[dict]:
    current = time.time() if now is None else float(now)
    conn = get_db_connection()
    try:
        bridge = _get_connection(conn, bridge_token)
        conn.execute(
            "UPDATE mobile_battery_ha_connections SET last_seen_at = ? WHERE connection_id = ?",
            (current, bridge["connection_id"]),
        )
        conn.commit()
        rows = conn.execute(
            "SELECT candidate_id, entity_id FROM mobile_battery_ha_candidates "
            "WHERE connection_id = ? AND selected = 1 ORDER BY entity_id",
            (bridge["connection_id"],),
        ).fetchall()
        return [{"candidate_id": row["candidate_id"], "entity_id": row["entity_id"]} for row in rows]
    finally:
        conn.close()


def report_selected_candidate(
    bridge_token: str,
    candidate_id: str,
    battery_percent: int,
    observed_at: datetime,
    now: datetime | None = None,
) -> dict:
    conn = get_db_connection()
    try:
        bridge = _get_connection(conn, bridge_token)
        row = conn.execute(
            "SELECT c.mobile_battery_device_id FROM mobile_battery_ha_candidates c "
            "JOIN mobile_battery_devices d ON d.device_id = c.mobile_battery_device_id "
            "WHERE c.candidate_id = ? AND c.connection_id = ? AND c.selected = 1 AND d.active = 1",
            (candidate_id, bridge["connection_id"]),
        ).fetchone()
        if row is None:
            raise HomeAssistantBridgeAuthenticationError()
        device_id = row["mobile_battery_device_id"]
    finally:
        conn.close()
    return process_mobile_battery_device_report(device_id, battery_percent, observed_at, now=now)


def revoke_connection(connection_id: str, now: float | None = None) -> bool:
    current = time.time() if now is None else float(now)
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT connection_id FROM mobile_battery_ha_connections "
            "WHERE connection_id = ? AND active = 1",
            (connection_id,),
        ).fetchone()
        if row is None:
            conn.rollback()
            return False
        conn.execute(
            "UPDATE mobile_battery_ha_connections SET active = 0, last_seen_at = ? WHERE connection_id = ?",
            (current, connection_id),
        )
        conn.execute(
            "UPDATE mobile_battery_ha_candidates SET selected = 0 WHERE connection_id = ?",
            (connection_id,),
        )
        conn.execute(
            "UPDATE mobile_battery_devices SET active = 0 "
            "WHERE source_type = 'home_assistant' AND source_ref IN "
            "(SELECT candidate_id FROM mobile_battery_ha_candidates WHERE connection_id = ?)",
            (connection_id,),
        )
        conn.commit()
        return True
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()
