"""Bounded periodic cleanup for high-volume operational records."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from database import get_db_connection


DAY_SECONDS = 24 * 60 * 60
MAX_RETENTION_DAYS = 3650
DEFAULT_TELEMETRY_RETENTION_DAYS = 30
DEFAULT_ACTUATOR_AUDIT_RETENTION_DAYS = 365


def _configured_days(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    try:
        days = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer number of days") from exc
    if not 1 <= days <= MAX_RETENTION_DAYS:
        raise RuntimeError(f"{name} must be between 1 and {MAX_RETENTION_DAYS} days")
    return days


def _delete_expired(
    conn: sqlite3.Connection,
    table: str,
    cutoff: Any,
    batch_size: int,
) -> int:
    # Table names are internal constants below; values remain parameterized.
    total = 0
    while True:
        cursor = conn.execute(
            f"DELETE FROM {table} WHERE id IN ("
            f"SELECT id FROM {table} WHERE timestamp IS NOT NULL AND timestamp < ? "
            "ORDER BY id LIMIT ?)",
            (cutoff, batch_size),
        )
        removed = max(cursor.rowcount, 0)
        conn.commit()
        total += removed
        if removed < batch_size:
            return total


def validate_retention_configuration() -> None:
    _configured_days("NIVUS_TELEMETRY_RETENTION_DAYS", DEFAULT_TELEMETRY_RETENTION_DAYS)
    _configured_days(
        "NIVUS_ACTUATOR_AUDIT_RETENTION_DAYS",
        DEFAULT_ACTUATOR_AUDIT_RETENTION_DAYS,
    )


def cleanup_expired_records(
    *,
    now: datetime | None = None,
    telemetry_retention_days: int | None = None,
    actuator_audit_retention_days: int | None = None,
    batch_size: int = 5000,
) -> dict[str, int]:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    telemetry_days = (
        telemetry_retention_days
        if telemetry_retention_days is not None
        else _configured_days(
            "NIVUS_TELEMETRY_RETENTION_DAYS", DEFAULT_TELEMETRY_RETENTION_DAYS
        )
    )
    audit_days = (
        actuator_audit_retention_days
        if actuator_audit_retention_days is not None
        else _configured_days(
            "NIVUS_ACTUATOR_AUDIT_RETENTION_DAYS", DEFAULT_ACTUATOR_AUDIT_RETENTION_DAYS
        )
    )
    for name, days in (
        ("telemetry_retention_days", telemetry_days),
        ("actuator_audit_retention_days", audit_days),
    ):
        if not 1 <= days <= MAX_RETENTION_DAYS:
            raise ValueError(f"{name} must be between 1 and {MAX_RETENTION_DAYS}")

    telemetry_cutoff = int(now.timestamp()) - telemetry_days * DAY_SECONDS
    audit_cutoff = (now - timedelta(days=audit_days)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    try:
        return {
            "telemetry": _delete_expired(
                conn, "telemetry", telemetry_cutoff, batch_size
            ),
            "actuator_audit": _delete_expired(
                conn, "actuator_audit", audit_cutoff, batch_size
            ),
        }
    finally:
        conn.close()
