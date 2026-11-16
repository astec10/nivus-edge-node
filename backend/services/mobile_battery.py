"""Authenticated mobile battery reports and deterministic relay safety rule."""

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from database import get_db_connection
from services.mqtt import ALLOWED_MQTT_TOPICS, publish_mqtt

RELAY_TOPIC = "nivus/edge/relay1"
BATTERY_THRESHOLD = 20
MAX_REPORT_AGE_SECONDS = 60 * 60
MAX_FUTURE_SKEW_SECONDS = 60
FAILED_PUBLISH_RETRY_SECONDS = 5 * 60
MAX_EVENT_ROWS = 5000


class MobileBatteryAuthenticationError(Exception):
    """The supplied mobile source token is invalid or revoked."""


def _utc(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("Use timestamps com fuso horário.")
    return current.astimezone(timezone.utc)


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def register_mobile_battery_device(name: str) -> dict:
    clean_name = " ".join(name.split())
    if not 1 <= len(clean_name) <= 48:
        raise ValueError("O nome do dispositivo deve ter de 1 a 48 caracteres.")
    device_id = uuid.uuid4().hex
    token = secrets.token_urlsafe(32)
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO mobile_battery_devices (device_id, name, token_sha256) "
            "VALUES (?, ?, ?)",
            (device_id, clean_name, _token_digest(token)),
        )
        conn.commit()
        row = conn.execute(
            "SELECT created_at FROM mobile_battery_devices WHERE device_id = ?",
            (device_id,),
        ).fetchone()
        return {
            "device_id": device_id,
            "name": clean_name,
            "active": True,
            "created_at": row["created_at"] if row else None,
            "token": token,
        }
    finally:
        conn.close()


def list_mobile_battery_devices() -> list[dict]:
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT device_id, name, active, created_at, last_battery_percent, "
            "last_observed_at, low_battery_latched "
            "FROM mobile_battery_devices ORDER BY created_at, device_id"
        ).fetchall()
        devices = []
        for row in rows:
            item = dict(row)
            item["active"] = bool(item["active"])
            item["low_battery_latched"] = bool(item["low_battery_latched"])
            observed = item.pop("last_observed_at")
            item["last_observed_at"] = (
                datetime.fromtimestamp(observed, timezone.utc).isoformat(timespec="seconds")
                if observed is not None else None
            )
            devices.append(item)
        return devices
    finally:
        conn.close()


def revoke_mobile_battery_device(device_id: str) -> bool:
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "UPDATE mobile_battery_devices SET active = 0 "
            "WHERE device_id = ? AND active = 1",
            (device_id,),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def _record_event(conn, device_id, received_at, observed_epoch, battery_percent, action,
                  broker_accepted=False) -> int:
    cursor = conn.execute(
        "INSERT INTO mobile_battery_events "
        "(device_id, received_at, observed_at, battery_percent, action, broker_accepted) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (device_id, received_at, observed_epoch, battery_percent, action, int(broker_accepted)),
    )
    conn.execute(
        "DELETE FROM mobile_battery_events WHERE id <= "
        "(SELECT COALESCE(MAX(id), 0) - ? FROM mobile_battery_events)",
        (MAX_EVENT_ROWS,),
    )
    return int(cursor.lastrowid)


def process_mobile_battery_report(
    device_token: str,
    battery_percent: int,
    observed_at: datetime,
    now: datetime | None = None,
) -> dict:
    if type(battery_percent) is not int or not 0 <= battery_percent <= 100:
        raise ValueError("A bateria deve ser um número inteiro de 0 a 100.")
    if not isinstance(device_token, str) or not 40 <= len(device_token) <= 128:
        raise MobileBatteryAuthenticationError()

    current = _utc(now)
    observed = _utc(observed_at)
    age = (current - observed).total_seconds()
    if age < -MAX_FUTURE_SKEW_SECONDS:
        raise ValueError("O horário da leitura está no futuro.")

    received_at = current.isoformat(timespec="seconds")
    observed_epoch = observed.timestamp()
    current_epoch = current.timestamp()
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        device = conn.execute(
            "SELECT device_id, last_observed_at, last_off_attempt_at, low_battery_latched "
            "FROM mobile_battery_devices WHERE token_sha256 = ? AND active = 1",
            (_token_digest(device_token),),
        ).fetchone()
        if device is None:
            conn.rollback()
            raise MobileBatteryAuthenticationError()

        if age > MAX_REPORT_AGE_SECONDS:
            conn.rollback()
            return {
                "status": "ignored", "action": "none", "reason": "stale_reading",
                "message": "Leitura antiga ignorada; nenhum comando foi enviado.",
            }

        if device["last_observed_at"] is not None and observed_epoch <= float(device["last_observed_at"]):
            conn.rollback()
            return {
                "status": "ignored", "action": "none", "reason": "duplicate_or_out_of_order",
                "message": "Leitura repetida ou fora de ordem ignorada.",
            }

        device_id = device["device_id"]
        if battery_percent > BATTERY_THRESHOLD:
            _record_event(conn, device_id, received_at, observed_epoch, battery_percent, "observed")
            conn.execute(
                "UPDATE mobile_battery_devices SET last_battery_percent = ?, "
                "last_observed_at = ?, last_off_attempt_at = NULL, low_battery_latched = 0 "
                "WHERE device_id = ?",
                (battery_percent, observed_epoch, device_id),
            )
            conn.commit()
            return {
                "status": "recorded", "action": "none", "reason": "above_threshold",
                "message": "Leitura registrada; a recuperação da bateria não envia ON.",
            }

        if device["low_battery_latched"]:
            _record_event(conn, device_id, received_at, observed_epoch, battery_percent,
                          "off_already_sent")
            conn.execute(
                "UPDATE mobile_battery_devices SET last_battery_percent = ?, last_observed_at = ? "
                "WHERE device_id = ?",
                (battery_percent, observed_epoch, device_id),
            )
            conn.commit()
            return {
                "status": "recorded", "action": "none", "reason": "off_already_sent",
                "message": "OFF já foi enviado para esta faixa baixa de bateria.",
            }

        last_attempt = device["last_off_attempt_at"]
        if last_attempt is not None and current_epoch - float(last_attempt) < FAILED_PUBLISH_RETRY_SECONDS:
            _record_event(conn, device_id, received_at, observed_epoch, battery_percent,
                          "off_retry_limited")
            conn.execute(
                "UPDATE mobile_battery_devices SET last_battery_percent = ?, last_observed_at = ? "
                "WHERE device_id = ?",
                (battery_percent, observed_epoch, device_id),
            )
            conn.commit()
            return {
                "status": "recorded", "action": "none", "reason": "retry_cooldown",
                "message": "Nova tentativa de OFF adiada para evitar repetição durante falha do broker.",
            }

        event_id = _record_event(conn, device_id, received_at, observed_epoch, battery_percent,
                                 "off_pending")
        conn.execute(
            "UPDATE mobile_battery_devices SET last_battery_percent = ?, last_observed_at = ?, "
            "last_off_attempt_at = ? WHERE device_id = ?",
            (battery_percent, observed_epoch, current_epoch, device_id),
        )
        conn.commit()
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()

    broker_accepted = False
    if RELAY_TOPIC in ALLOWED_MQTT_TOPICS:
        try:
            broker_accepted = bool(publish_mqtt(RELAY_TOPIC, "OFF"))
        except Exception:
            broker_accepted = False

    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "UPDATE mobile_battery_events SET action = ?, broker_accepted = ? WHERE id = ?",
            ("off_sent" if broker_accepted else "off_failed", int(broker_accepted), event_id),
        )
        if broker_accepted:
            conn.execute(
                "UPDATE mobile_battery_devices SET low_battery_latched = "
                "CASE WHEN last_battery_percent <= ? THEN 1 ELSE 0 END "
                "WHERE device_id = ? AND active = 1",
                (BATTERY_THRESHOLD, device_id),
            )
            conn.execute(
                "INSERT INTO actuator_audit (topic, command, source) "
                "VALUES (?, 'OFF', 'mobile_battery')",
                (RELAY_TOPIC,),
            )
        conn.commit()
    finally:
        conn.close()

    if broker_accepted:
        return {
            "status": "recorded", "action": "OFF", "broker_accepted": True,
            "device_confirmed": False,
            "message": "Broker aceitou OFF; o relé físico não confirmou o estado.",
        }
    return {
        "status": "recorded", "action": "none", "broker_accepted": False,
        "reason": "broker_unavailable",
        "message": "Broker não confirmou OFF. Uma nova tentativa ficará limitada a uma por 5 minutos.",
    }
