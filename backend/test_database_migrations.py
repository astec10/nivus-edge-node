import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database


class ThermalMigrationTests(unittest.TestCase):
    def test_adds_source_and_hotspot_columns_without_losing_rows(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "legacy.db"
            conn = sqlite3.connect(db_path)
            conn.execute(
                """CREATE TABLE telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node TEXT,
                    timestamp INTEGER,
                    cpu_percent REAL,
                    memory_percent REAL,
                    disk_percent REAL,
                    temperature REAL,
                    power_consumption REAL
                )"""
            )
            conn.execute(
                "INSERT INTO telemetry (node,timestamp,temperature) VALUES (?,?,?)",
                ("fixture", 100, 29.8),
            )
            conn.commit()
            conn.close()

            with patch.object(database, "DB_PATH", db_path):
                database.init_db()
                conn = database.get_db_connection()
                columns = {row["name"] for row in conn.execute("PRAGMA table_info(telemetry)")}
                row = conn.execute(
                    "SELECT node,timestamp,temperature FROM telemetry WHERE id=1"
                ).fetchone()
                quick_check = conn.execute("PRAGMA quick_check").fetchone()[0]
                conn.close()

            self.assertEqual(quick_check, "ok")
            self.assertEqual((row["node"], row["timestamp"], row["temperature"]), ("fixture", 100, 29.8))
            self.assertTrue(
                {
                    "temperature_source",
                    "cpu_hotspot_temperature",
                    "cpu_hotspot_source",
                    "motherboard_temperature_source",
                    "gpu_temperature_source",
                    "gpu_hotspot_temperature",
                    "gpu_hotspot_source",
                }.issubset(columns)
            )


if __name__ == "__main__":
    unittest.main()
