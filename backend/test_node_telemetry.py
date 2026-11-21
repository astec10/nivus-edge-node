import hashlib
import math
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import database
from api.routers import nodes as node_routes
from api.routers.nodes import NodeTelemetryEnvelope
from fastapi import HTTPException, Response
from pydantic import ValidationError
from services import nodes
from services.node_telemetry import (
    MAX_TELEMETRY_HISTORY_OFFSET,
    TELEMETRY_MIN_INTERVAL_SECONDS,
    TELEMETRY_RETENTION_SECONDS,
    TelemetryRateLimitError,
    get_node_telemetry_history,
    get_node_telemetry_history_page,
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

    def test_oversized_integer_metric_returns_validation_error(self):
        sample = {
            "metric": "cpu.utilization",
            "value": 10 ** 1000,
            "unit": "percent",
            "quality": "measured",
        }
        with self.assertRaisesRegex(ValueError, "número finito"):
            normalize_telemetry_samples([sample])

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

    def test_history_page_reports_stable_count_and_range_for_older_pages(self):
        first = self.ingest(0, now=self.now)
        second = self.ingest(1, now=self.now + timedelta(seconds=30))
        third = self.ingest(2, now=self.now + timedelta(seconds=60))
        since = self.now - timedelta(days=14)
        snapshot_now = self.now + timedelta(seconds=90)

        newest = get_node_telemetry_history_page(
            self.node["node_id"], since=since, limit=2, offset=0, now=snapshot_now
        )
        self.assertEqual(newest["snapshot_until"], snapshot_now.isoformat(timespec="milliseconds").replace("+00:00", "Z"))

        # A batch arriving after page one must not alter the snapshot or shift page two.
        fourth = self.ingest(3, now=snapshot_now + timedelta(seconds=30))
        oldest = get_node_telemetry_history_page(
            self.node["node_id"],
            since=since,
            limit=2,
            offset=2,
            snapshot_until=newest["snapshot_until"],
            now=snapshot_now + timedelta(seconds=30),
        )

        self.assertEqual(newest["total_batches"], 3)
        self.assertEqual(len(newest["batches"]), 2)
        self.assertTrue(newest["has_more"])
        self.assertEqual(newest["range_start"], second["received_at"])
        self.assertEqual(newest["range_end"], third["received_at"])
        self.assertFalse(oldest["has_more"])
        self.assertEqual(oldest["batches"][0]["received_at"], first["received_at"])
        self.assertEqual(oldest["total_batches"], newest["total_batches"])
        self.assertNotIn(fourth["received_at"], [item["received_at"] for item in oldest["batches"]])

    def test_fourteen_day_history_gaps_offline_and_spikes_are_navigable_with_bounded_pages(self):
        conn = database.get_db_connection()
        now_epoch = self.now.timestamp()
        start = now_epoch - TELEMETRY_RETENTION_SECONDS
        generated = TELEMETRY_RETENTION_SECONDS // TELEMETRY_MIN_INTERVAL_SECONDS + 1
        skipped_index = generated // 2
        session_hash = hashlib.sha256(self.node["session_id"].encode("utf-8")).hexdigest()
        try:
            conn.execute("BEGIN IMMEDIATE")
            for index in range(generated):
                if index == skipped_index:
                    continue
                received_at = start + index * TELEMETRY_MIN_INTERVAL_SECONDS
                value = 100.0 if index in (0, generated - 1) else float(index % 80)
                batch_cursor = conn.execute(
                    "INSERT INTO node_telemetry_batches "
                    "(node_id, session_sha256, sequence, schema_version, observed_at, received_at, payload_sha256) "
                    "VALUES (?, ?, ?, 1, ?, ?, ?)",
                    (
                        self.node["node_id"],
                        session_hash,
                        index,
                        received_at,
                        received_at,
                        hashlib.sha256(f"synthetic-{index}".encode("utf-8")).hexdigest(),
                    ),
                )
                conn.execute(
                    "INSERT INTO node_telemetry_samples (batch_id, metric, value, unit, quality) "
                    "VALUES (?, 'cpu.utilization', ?, 'percent', 'measured')",
                    (batch_cursor.lastrowid, value),
                )
            expired_at = now_epoch - TELEMETRY_RETENTION_SECONDS - 1
            expired_cursor = conn.execute(
                "INSERT INTO node_telemetry_batches "
                "(node_id, session_sha256, sequence, schema_version, observed_at, received_at, payload_sha256) "
                "VALUES (?, ?, ?, 1, ?, ?, ?)",
                (
                    self.node["node_id"],
                    session_hash,
                    generated + 1,
                    expired_at,
                    expired_at,
                    hashlib.sha256(b"expired-synthetic").hexdigest(),
                ),
            )
            conn.execute(
                "INSERT INTO node_telemetry_samples (batch_id, metric, value, unit, quality) "
                "VALUES (?, 'cpu.utilization', 88, 'percent', 'measured')",
                (expired_cursor.lastrowid,),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        since = self.now - timedelta(days=14)
        newest = get_node_telemetry_history_page(
            self.node["node_id"], since=since, limit=500, offset=0, now=self.now
        )
        self.assertEqual(newest["total_batches"], generated - 1)
        self.assertEqual(newest["snapshot_until"], self.now.isoformat(timespec="milliseconds").replace("+00:00", "Z"))

        pages = [newest]
        for offset in range(500, newest["total_batches"], 500):
            pages.append(get_node_telemetry_history_page(
                self.node["node_id"],
                since=since,
                limit=500,
                offset=offset,
                snapshot_until=newest["snapshot_until"],
                now=self.now,
            ))

        self.assertEqual(len(pages), math.ceil((generated - 1) / 500))
        self.assertTrue(all(len(page["batches"]) <= 500 for page in pages))
        self.assertEqual(len(pages[-1]["batches"]), (generated - 1) % 500)
        self.assertTrue(all(page["has_more"] for page in pages[:-1]))
        self.assertFalse(pages[-1]["has_more"])
        self.assertEqual(pages[0]["batches"][-1]["samples"][0]["value"], 100.0)
        self.assertEqual(pages[-1]["batches"][0]["samples"][0]["value"], 100.0)

        chronological = [batch for page in reversed(pages) for batch in page["batches"]]
        received_times = [item["received_at"] for item in chronological]
        self.assertEqual(len(received_times), generated - 1)
        self.assertEqual(len(set(received_times)), generated - 1)
        parsed_times = [datetime.fromisoformat(value.replace("Z", "+00:00")) for value in received_times]
        self.assertTrue(all(left < right for left, right in zip(parsed_times, parsed_times[1:])))
        self.assertEqual(
            (parsed_times[skipped_index] - parsed_times[skipped_index - 1]).total_seconds(),
            TELEMETRY_MIN_INTERVAL_SECONDS * 2,
        )

        offline_view = get_node_telemetry_history_page(
            self.node["node_id"],
            since=since,
            limit=500,
            offset=0,
            snapshot_until=newest["snapshot_until"],
            now=self.now + timedelta(hours=1),
        )
        self.assertLess(offline_view["total_batches"], newest["total_batches"])
        self.assertEqual(offline_view["range_end"], newest["range_end"])

    def test_history_route_keeps_list_body_and_exposes_bounded_pagination_headers(self):
        page = {
            "batches": [{"received_at": "2026-11-21T12:00:00.000Z"}],
            "total_batches": 1,
            "offset": 0,
            "limit": 1,
            "has_more": False,
            "range_start": "2026-11-21T12:00:00.000Z",
            "range_end": "2026-11-21T12:00:00.000Z",
            "snapshot_until": "2026-11-21T12:00:00.000Z",
        }
        response = Response()
        since = self.now - timedelta(minutes=5)
        with patch.object(node_routes, "get_node_telemetry_history_page", return_value=page) as query:
            batches = node_routes.get_node_telemetry(
                self.node["node_id"],
                response=response,
                since=since,
                limit=1,
                offset=0,
                snapshot_until=None,
                admin="admin",
            )

        self.assertEqual(batches, page["batches"])
        query.assert_called_once_with(
            self.node["node_id"],
            since=since,
            limit=1,
            offset=0,
            snapshot_until=None,
        )
        self.assertEqual(response.headers["X-Nivus-History-Pagination"], "offset-v1")
        self.assertEqual(response.headers["X-Nivus-History-Total-Batches"], "1")
        self.assertEqual(response.headers["X-Nivus-History-Offset"], "0")
        self.assertEqual(response.headers["X-Nivus-History-Limit"], "1")
        self.assertEqual(response.headers["X-Nivus-History-Has-More"], "false")
        self.assertEqual(
            response.headers["X-Nivus-History-Snapshot-Until"],
            page["snapshot_until"],
        )

    def test_history_page_rejects_boolean_and_excessive_offsets(self):
        for offset in (True, -1, MAX_TELEMETRY_HISTORY_OFFSET + 1):
            with self.subTest(offset=offset):
                with self.assertRaises(ValueError):
                    get_node_telemetry_history_page(
                        self.node["node_id"], limit=500, offset=offset, now=self.now
                    )

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
