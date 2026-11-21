import math
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import database
from api.routers import nodes as node_routes
from api.routers.nodes import NodeTelemetryEnvelope
from fastapi import HTTPException
from pydantic import ValidationError
from services import nodes
from services.node_telemetry import (
    TELEMETRY_MIN_INTERVAL_SECONDS,
    TELEMETRY_RETENTION_SECONDS,
    TelemetryRateLimitError,
    get_node_telemetry_history,
    normalize_telemetry_samples,
    process_node_telemetry,
)


class NodeTelemetryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(database, "DB_PATH", Path(self.temp_dir.name) / "nivus.db")
        self.db_patch.start()
        database.init_db()
        self.now = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)
        enrollment = nodes.create_node_enrollment(now=self.now.timestamp())
        self.node = nodes.enroll_node(enrollment["code"], "Edge Telemetria", now=self.now.timestamp())

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    @staticmethod
    def samples(cpu=25.0):
        return [
            {"metric": "cpu.utilization", "value": cpu, "unit": "percent", "quality": "measured"},
            {"metric": "memory.utilization", "value": 40, "unit": "percent", "quality": "measured"},
            {"metric": "gpu.temperature", "value": None, "unit": "celsius", "quality": "unavailable"},
        ]

    def ingest(self, sequence, samples=None, observed_at=None, now=None):
        return process_node_telemetry(
            self.node["token"],
            self.node["session_id"],
            sequence,
            1,
            observed_at or self.now,
            self.samples() if samples is None else samples,
            now=(now or self.now).timestamp() if isinstance(now or self.now, datetime) else now,
        )

    def test_api_schema_requires_timezone_strict_sequence_and_unique_metric_names(self):
        payload = {
            "session_id": self.node["session_id"],
            "sequence": 0,
            "schema_version": 1,
            "observed_at": self.now.isoformat(),
            "samples": self.samples(),
        }
        self.assertEqual(NodeTelemetryEnvelope.model_validate(payload).sequence, 0)

        for invalid in (
            {**payload, "sequence": True},
            {**payload, "observed_at": self.now.replace(tzinfo=None).isoformat()},
            {**payload, "schema_version": 2},
            {**payload, "extra": "not allowed"},
            {**payload, "samples": self.samples() + [self.samples()[0]]},
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValidationError):
                    NodeTelemetryEnvelope.model_validate(invalid)

    def test_invalid_metrics_units_ranges_boolean_and_nan_are_rejected(self):
        invalid_samples = (
            [{"metric": "cpu.utilization", "value": True, "unit": "percent", "quality": "measured"}],
            [{"metric": "cpu.utilization", "value": 101, "unit": "percent", "quality": "measured"}],
            [{"metric": "cpu.utilization", "value": 20, "unit": "celsius", "quality": "measured"}],
            [{"metric": "cpu.utilization", "value": None, "unit": "percent", "quality": "measured"}],
            [{"metric": "gpu.temperature", "value": 90, "unit": "celsius", "quality": "unavailable"}],
            [{"metric": "unknown.metric", "value": 1, "unit": "percent", "quality": "measured"}],
            [{"metric": "cpu.utilization", "value": math.nan, "unit": "percent", "quality": "measured"}],
            [{"metric": "cpu.utilization", "value": 1, "unit": "percent", "quality": []}],
        )
        for value in invalid_samples:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_telemetry_samples(value)

    def test_exact_retry_is_idempotent_and_conflicting_replay_is_rejected(self):
        first = self.ingest(0)
        duplicate = self.ingest(0)
        self.assertFalse(first["duplicate"])
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(duplicate["received_at"], first["received_at"])
        self.assertEqual(len(get_node_telemetry_history(self.node["node_id"])), 1)

        with self.assertRaises(nodes.HeartbeatReplayError):
            self.ingest(0, samples=self.samples(cpu=26.0))
        with self.assertRaises(nodes.HeartbeatReplayError):
            self.ingest(0, observed_at=self.now + timedelta(seconds=1))

    def test_heartbeat_and_telemetry_share_sequence_replay_boundary(self):
        accepted = self.ingest(0)
        heartbeat = nodes.process_node_heartbeat(
            self.node["token"], self.node["session_id"], 1,
            "1.0.0", 1, ["telemetry.cpu"], now=self.now.timestamp() + 1,
        )
        self.assertEqual(heartbeat["status"], "ok")

        # An exact retry stays idempotent even if a newer heartbeat advanced
        # the shared sequence. A conflicting reuse of that old sequence is a replay.
        duplicate = self.ingest(0, now=self.now + timedelta(seconds=2))
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(duplicate["received_at"], accepted["received_at"])
        with self.assertRaises(nodes.HeartbeatReplayError):
            self.ingest(0, samples=self.samples(cpu=26.0), now=self.now + timedelta(seconds=2))
        self.assertEqual(len(get_node_telemetry_history(self.node["node_id"])), 1)

    def test_history_is_per_node_chronological_and_reports_clock_skew(self):
        first = self.ingest(0, observed_at=self.now - timedelta(seconds=3), now=self.now)
        second = self.ingest(
            1,
            observed_at=self.now + timedelta(seconds=32),
            now=self.now + timedelta(seconds=TELEMETRY_MIN_INTERVAL_SECONDS),
        )
        history = get_node_telemetry_history(self.node["node_id"], limit=2)
        self.assertEqual([item["received_at"] for item in history], [first["received_at"], second["received_at"]])
        self.assertEqual(history[0]["clock_skew_seconds"], 3.0)
        self.assertEqual(history[1]["clock_skew_seconds"], -2.0)
        self.assertEqual(history[0]["samples"][0]["metric"], "cpu.utilization")
        self.assertNotIn("token", history[0])
        self.assertNotIn("session_id", history[0])

    def test_retention_removes_batches_older_than_fourteen_days(self):
        self.ingest(0)
        later = self.now + timedelta(seconds=TELEMETRY_RETENTION_SECONDS + 1)
        # An idle node must not keep exposing expired records merely because it
        # has not sent a new batch since the retention window elapsed.
        history = get_node_telemetry_history(self.node["node_id"], now=later)
        self.assertEqual(history, [])
        conn = database.get_db_connection()
        try:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM node_telemetry_batches").fetchone()[0],
                0,
            )
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM node_telemetry_samples").fetchone()[0],
                0,
            )
        finally:
            conn.close()

    def test_history_since_cannot_include_expired_batches(self):
        self.ingest(0)
        later = self.now + timedelta(seconds=TELEMETRY_RETENTION_SECONDS + 1)
        self.ingest(1, observed_at=later, now=later)
        history = get_node_telemetry_history(
            self.node["node_id"], since=self.now - timedelta(days=30), now=later,
        )
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["observed_at"], later.isoformat(timespec="milliseconds").replace("+00:00", "Z"))

    def test_rate_limit_is_per_node_across_session_renewal_and_exact_retries(self):
        first = self.ingest(0)
        duplicate = self.ingest(0, now=self.now + timedelta(seconds=1))
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(first["received_at"], duplicate["received_at"])

        session = nodes.create_node_session(self.node["token"])
        with self.assertRaises(TelemetryRateLimitError) as raised:
            process_node_telemetry(
                self.node["token"], session["session_id"], 0, 1,
                self.now + timedelta(seconds=10), self.samples(),
                now=self.now.timestamp() + 10,
            )
        self.assertEqual(
            raised.exception.retry_after_seconds,
            TELEMETRY_MIN_INTERVAL_SECONDS - 10,
        )

        accepted = process_node_telemetry(
            self.node["token"], session["session_id"], 0, 1,
            self.now + timedelta(seconds=TELEMETRY_MIN_INTERVAL_SECONDS),
            self.samples(),
            now=self.now.timestamp() + TELEMETRY_MIN_INTERVAL_SECONDS,
        )
        self.assertFalse(accepted["duplicate"])
        self.assertEqual(len(get_node_telemetry_history(self.node["node_id"])), 2)

    def test_rate_limit_maps_to_http_429_with_retry_after(self):
        payload = NodeTelemetryEnvelope.model_validate({
            "session_id": self.node["session_id"],
            "sequence": 0,
            "schema_version": 1,
            "observed_at": self.now.isoformat(),
            "samples": self.samples(),
        })
        with patch.object(
            node_routes,
            "process_node_telemetry",
            side_effect=TelemetryRateLimitError(7),
        ):
            with self.assertRaises(HTTPException) as raised:
                node_routes.ingest_telemetry(payload, self.node["token"])
        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(raised.exception.headers["Retry-After"], "7")

    def test_revoked_or_unknown_node_cannot_submit_telemetry(self):
        self.assertTrue(nodes.revoke_node(self.node["node_id"], now=self.now.timestamp() + 1))
        with self.assertRaises(nodes.NodeAuthenticationError):
            self.ingest(0, now=self.now + timedelta(seconds=2))
        with self.assertRaises(nodes.NodeAuthenticationError):
            process_node_telemetry("x" * 43, self.node["session_id"], 0, 1, self.now, self.samples(), now=self.now.timestamp())

    def test_nonfinite_or_unrepresentable_timestamp_is_rejected(self):
        for invalid in (math.nan, math.inf, -math.inf, 1e100):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    self.ingest(0, observed_at=invalid)


if __name__ == "__main__":
    unittest.main()
