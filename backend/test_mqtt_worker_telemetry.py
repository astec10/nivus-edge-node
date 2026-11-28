import json
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import database
import mqtt_worker


class MqttTelemetryWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(database, "DB_PATH", Path(self.temp_dir.name) / "telemetry.db")
        self.db_patch.start()
        database.init_db()

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def send(self, payload):
        message = SimpleNamespace(payload=json.dumps(payload, allow_nan=True).encode("utf-8"))
        with patch.object(mqtt_worker, "maintenance_enabled", return_value=False):
            mqtt_worker.on_message(None, None, message)

    def base_payload(self):
        return {
            "node": "synthetic-node",
            "timestamp": 100,
            "cpu_percent": 25,
            "memory_percent": 40,
            "disk_percent": 60,
            "power_consumption": None,
        }

    def fetch_rows(self):
        conn = database.get_db_connection()
        try:
            return conn.execute(
                "SELECT cpu_percent,cpu_source,cpu_per_core_json,cpu_per_core_source,"
                "memory_percent,memory_source,disk_percent,disk_source FROM telemetry"
            ).fetchall()
        finally:
            conn.close()

    def test_old_payload_without_sources_or_per_core_data_remains_accepted(self):
        self.send(self.base_payload())
        rows = self.fetch_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["cpu_percent"], 25)
        self.assertIsNone(rows[0]["cpu_source"])
        self.assertIsNone(rows[0]["cpu_per_core_json"])
        self.assertIsNone(rows[0]["cpu_per_core_source"])
        self.assertIsNone(rows[0]["memory_source"])
        self.assertIsNone(rows[0]["disk_source"])

    def test_valid_per_core_series_and_collector_origins_are_stored(self):
        payload = self.base_payload()
        payload.update({
            "cpu_source": "psutil.cpu_percent",
            "cpu_per_core_percent": [12.5, 0, 100],
            "cpu_per_core_source": "psutil.cpu_percent(percpu=True)",
            "memory_source": "psutil.virtual_memory",
            "disk_source": "psutil.disk_usage",
        })
        self.send(payload)
        rows = self.fetch_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["cpu_per_core_json"], "[12.5,0.0,100.0]")
        self.assertEqual(rows[0]["cpu_source"], "psutil.cpu_percent")
        self.assertEqual(rows[0]["cpu_per_core_source"], "psutil.cpu_percent(percpu=True)")
        self.assertEqual(rows[0]["memory_source"], "psutil.virtual_memory")
        self.assertEqual(rows[0]["disk_source"], "psutil.disk_usage")

    def test_invalid_per_core_values_are_rejected_without_storing_sample(self):
        invalid_series = ([True], [101], [-1], [math.nan], ["20"], [None] * 257)
        for values in invalid_series:
            with self.subTest(values=str(values[:3])):
                payload = self.base_payload()
                payload["cpu_per_core_percent"] = values
                self.send(payload)
                self.assertEqual(self.fetch_rows(), [])


if __name__ == "__main__":
    unittest.main()
