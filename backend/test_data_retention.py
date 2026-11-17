import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import database
from services.data_retention import cleanup_expired_records


class DataRetentionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(database, "DB_PATH", Path(self.temp_dir.name) / "nivus.db")
        self.db_patch.start()
        database.init_db()

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_cleanup_removes_expired_rows_in_batches_and_keeps_recent_rows(self):
        now = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
        old_timestamp = int((now - timedelta(days=31)).timestamp())
        recent_timestamp = int((now - timedelta(days=2)).timestamp())
        old_audit = (now - timedelta(days=366)).strftime("%Y-%m-%d %H:%M:%S")
        recent_audit = (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")

        conn = database.get_db_connection()
        try:
            conn.executemany(
                "INSERT INTO telemetry (timestamp) VALUES (?)",
                [(old_timestamp,)] * 5 + [(recent_timestamp,)],
            )
            conn.executemany(
                "INSERT INTO actuator_audit (timestamp, topic, command) "
                "VALUES (?, ?, ?)",
                [(old_audit, "nivus/test", "OFF")] * 3
                + [(recent_audit, "nivus/test", "OFF")],
            )
            conn.commit()
        finally:
            conn.close()

        removed = cleanup_expired_records(
            now=now,
            telemetry_retention_days=30,
            actuator_audit_retention_days=365,
            batch_size=2,
        )

        self.assertEqual(removed, {"telemetry": 5, "actuator_audit": 3})
        conn = database.get_db_connection()
        try:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM telemetry").fetchone()[0], 1
            )
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM actuator_audit").fetchone()[0], 1
            )
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
