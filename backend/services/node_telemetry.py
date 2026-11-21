"""Versioned, bounded telemetry ingestion for enrolled Nivus nodes."""

import hashlib
import json
import math
import time
from datetime import datetime, timezone

from database import get_db_connection
from services.nodes import HeartbeatReplayError, NodeAuthenticationError

TELEMETRY_SCHEMA_VERSION = 1
TELEMETRY_RETENTION_SECONDS = 14 * 24 * 60 * 60
TELEMETRY_MIN_INTERVAL_SECONDS = 30
MAX_TELEMETRY_SAMPLES = 32


class TelemetryRateLimitError(Exception):
    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = max(1, int(retry_after_seconds))
        super().__init__("O intervalo mínimo entre lotes de telemetria ainda não terminou.")

# Metric names are versioned API identifiers. Units and ranges are validated
# here and at the database boundary; adding a metric requires a schema change.
METRIC_SPECS = {
    "cpu.utilization": ("percent", 0.0, 100.0),
    "memory.utilization": ("percent", 0.0, 100.0),
    "disk.utilization": ("percent", 0.0, 100.0),
    "host_battery.level": ("percent", 0.0, 100.0),
    "cpu.temperature": ("celsius", -40.0, 150.0),
    "apu.temperature": ("celsius", -40.0, 150.0),
    "gpu.temperature": ("celsius", -40.0, 150.0),
    "motherboard.temperature": ("celsius", -40.0, 150.0),
    "power.estimated": ("watt", 0.0, 100_000.0),
}
QUALITY_VALUES = frozenset({"measured", "estimated", "unavailable"})


def _epoch(value=None) -> float:
    if value is None:
        return time.time()
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Use um horário de origem com fuso horário.")
        return value.astimezone(timezone.utc).timestamp()
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Horário de telemetria inválido.")
    epoch = float(value)
    if not math.isfinite(epoch):
        raise ValueError("Horário de telemetria inválido.")
    try:
        datetime.fromtimestamp(epoch, timezone.utc)
    except (OverflowError, OSError, ValueError):
        raise ValueError("Horário de telemetria fora da faixa permitida.") from None
    return epoch


def _iso(value: float) -> str:
    return datetime.fromtimestamp(value, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_telemetry_samples(samples) -> list[dict]:
    if not isinstance(samples, (list, tuple)) or not 1 <= len(samples) <= MAX_TELEMETRY_SAMPLES:
        raise ValueError("A amostra deve conter de 1 a 32 métricas.")

    normalized = []
    seen = set()
    for sample in samples:
        if not isinstance(sample, dict):
            raise ValueError("Formato de amostra inválido.")
        if set(sample) != {"metric", "value", "unit", "quality"}:
            raise ValueError("A amostra contém campos ausentes ou não permitidos.")
        metric = sample["metric"]
        unit = sample["unit"]
        quality = sample["quality"]
        value = sample["value"]
        if not isinstance(metric, str) or metric not in METRIC_SPECS:
            raise ValueError("Métrica não permitida para este esquema.")
        if metric in seen:
            raise ValueError("A amostra contém métricas duplicadas.")
        seen.add(metric)
        expected_unit, minimum, maximum = METRIC_SPECS[metric]
        if unit != expected_unit:
            raise ValueError("Unidade incompatível com a métrica.")
        if not isinstance(quality, str) or quality not in QUALITY_VALUES:
            raise ValueError("Qualidade da métrica inválida.")
        if quality == "unavailable":
            if value is not None:
                raise ValueError("Métrica indisponível deve ter valor nulo.")
            normalized_value = None
        else:
            if type(value) not in (int, float):
                raise ValueError("O valor da métrica deve ser um número finito.")
            try:
                normalized_value = float(value)
            except OverflowError:
                raise ValueError("O valor da métrica deve ser um número finito.") from None
            if not math.isfinite(normalized_value):
                raise ValueError("O valor da métrica deve ser um número finito.")
            if not minimum <= normalized_value <= maximum:
                raise ValueError("Valor fora da faixa permitida para a métrica.")
        normalized.append({
            "metric": metric,
            "value": normalized_value,
            "unit": unit,
            "quality": quality,
        })

    return sorted(normalized, key=lambda item: item["metric"])


def process_node_telemetry(
    node_token: str,
    session_id: str,
    sequence: int,
    schema_version: int,
    observed_at,
    samples,
    now=None,
) -> dict:
    received_at = _epoch(now)
    source_time = _epoch(observed_at)
    if not isinstance(node_token, str) or not 40 <= len(node_token) <= 128:
        raise NodeAuthenticationError()
    if not isinstance(session_id, str) or not 40 <= len(session_id) <= 128:
        raise NodeAuthenticationError()
    if type(sequence) is not int or not 0 <= sequence <= 2**63 - 1:
        raise ValueError("Sequência de telemetria inválida.")
    if type(schema_version) is not int or schema_version != TELEMETRY_SCHEMA_VERSION:
        raise ValueError("Versão de esquema de telemetria não suportada.")

    normalized_samples = normalize_telemetry_samples(samples)
    session_sha256 = _digest(session_id)
    canonical_payload = json.dumps(
        {
            "schema_version": schema_version,
            "observed_at": source_time,
            "samples": normalized_samples,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    payload_sha256 = _digest(canonical_payload)

    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        node = conn.execute(
            "SELECT node_id, session_sha256, last_sequence FROM nodes "
            "WHERE token_sha256 = ? AND active = 1",
            (_digest(node_token),),
        ).fetchone()
        if node is None or node["session_sha256"] != session_sha256:
            conn.rollback()
            raise NodeAuthenticationError()

        if sequence <= int(node["last_sequence"]):
            previous = conn.execute(
                "SELECT batch_id, received_at, payload_sha256 FROM node_telemetry_batches "
                "WHERE node_id = ? AND session_sha256 = ? AND sequence = ?",
                (node["node_id"], session_sha256, sequence),
            ).fetchone()
            if previous is None or previous["payload_sha256"] != payload_sha256:
                conn.rollback()
                raise HeartbeatReplayError()
            conn.commit()
            return {
                "status": "accepted",
                "node_id": node["node_id"],
                "received_at": _iso(float(previous["received_at"])),
                "observed_at": _iso(source_time),
                "clock_skew_seconds": round(float(previous["received_at"]) - source_time, 3),
                "schema_version": schema_version,
                "sample_count": len(normalized_samples),
                "duplicate": True,
            }

        previous_batch = conn.execute(
            "SELECT received_at FROM node_telemetry_batches "
            "WHERE node_id = ? ORDER BY received_at DESC, batch_id DESC LIMIT 1",
            (node["node_id"],),
        ).fetchone()
        if previous_batch is not None:
            elapsed = received_at - float(previous_batch["received_at"])
            if elapsed < TELEMETRY_MIN_INTERVAL_SECONDS:
                retry_after = math.ceil(TELEMETRY_MIN_INTERVAL_SECONDS - elapsed)
                conn.rollback()
                raise TelemetryRateLimitError(retry_after)

        cursor = conn.execute(
            "INSERT INTO node_telemetry_batches "
            "(node_id, session_sha256, sequence, schema_version, observed_at, received_at, payload_sha256) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                node["node_id"], session_sha256, sequence, schema_version,
                source_time, received_at, payload_sha256,
            ),
        )
        batch_id = cursor.lastrowid
        conn.executemany(
            "INSERT INTO node_telemetry_samples (batch_id, metric, value, unit, quality) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (batch_id, item["metric"], item["value"], item["unit"], item["quality"])
                for item in normalized_samples
            ],
        )
        conn.execute(
            "UPDATE nodes SET last_seen = ?, last_sequence = ? "
            "WHERE node_id = ? AND active = 1",
            (received_at, sequence, node["node_id"]),
        )
        conn.execute(
            "DELETE FROM node_telemetry_batches WHERE received_at < ?",
            (received_at - TELEMETRY_RETENTION_SECONDS,),
        )
        conn.commit()
        return {
            "status": "accepted",
            "node_id": node["node_id"],
            "received_at": _iso(received_at),
            "observed_at": _iso(source_time),
            "clock_skew_seconds": round(received_at - source_time, 3),
            "schema_version": schema_version,
            "sample_count": len(normalized_samples),
            "duplicate": False,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_node_telemetry_history(node_id: str, since=None, limit: int = 120, now=None) -> list[dict]:
    if not isinstance(node_id, str) or len(node_id) != 32 or any(char not in "0123456789abcdef" for char in node_id):
        raise ValueError("Identificador de nó inválido.")
    if type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError("O limite deve estar entre 1 e 500 amostras.")
    retention_cutoff = _epoch(now) - TELEMETRY_RETENTION_SECONDS
    received_after = max(_epoch(since), retention_cutoff) if since is not None else retention_cutoff
    sql = (
        "WITH recent_batches AS ("
        "SELECT batch_id, node_id, schema_version, observed_at, received_at "
        "FROM node_telemetry_batches WHERE node_id = ? AND received_at >= ?"
    )
    params = [node_id, received_after]
    sql += " ORDER BY received_at DESC, batch_id DESC LIMIT ?) "
    params.append(limit)
    sql += (
        "SELECT b.batch_id, b.node_id, b.schema_version, b.observed_at, b.received_at, "
        "s.metric, s.value, s.unit, s.quality FROM recent_batches b "
        "JOIN node_telemetry_samples s ON s.batch_id = b.batch_id "
        "ORDER BY b.received_at ASC, b.batch_id ASC, s.metric ASC"
    )

    conn = get_db_connection()
    try:
        # Keep the retention contract consistent even when this node has gone
        # offline and no new telemetry batch arrives to trigger ingestion cleanup.
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "DELETE FROM node_telemetry_batches WHERE received_at < ?",
            (retention_cutoff,),
        )
        rows = conn.execute(sql, params).fetchall()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    batches = {}
    for row in rows:
        batch_id = int(row["batch_id"])
        batch = batches.get(batch_id)
        if batch is None:
            observed_at = float(row["observed_at"])
            received_at = float(row["received_at"])
            batch = {
                "node_id": row["node_id"],
                "schema_version": int(row["schema_version"]),
                "observed_at": _iso(observed_at),
                "received_at": _iso(received_at),
                "clock_skew_seconds": round(received_at - observed_at, 3),
                "samples": [],
            }
            batches[batch_id] = batch
        batch["samples"].append({
            "metric": row["metric"],
            "value": float(row["value"]) if row["value"] is not None else None,
            "unit": row["unit"],
            "quality": row["quality"],
        })
    return list(batches.values())
