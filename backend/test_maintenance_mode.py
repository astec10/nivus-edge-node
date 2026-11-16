import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
from services import maintenance


class MaintenanceModeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.db_path = root / "nivus.db"
        self.state_path = root / "run" / "state.json"
        self.db_patch = patch.object(database, "DB_PATH", self.db_path)
        self.db_patch.start()
        self.env_patch = patch.dict(
            os.environ,
            {"NIVUS_MAINTENANCE_STATE_PATH": str(self.state_path)},
        )
        self.env_patch.start()
        database.init_db()

    def tearDown(self):
        self.env_patch.stop()
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def audit_rows(self):
        conn = database.get_db_connection()
        try:
            return conn.execute(
                "SELECT actor, enabled, boot_id, reason FROM maintenance_audit ORDER BY id"
            ).fetchall()
        finally:
            conn.close()

    def test_missing_marker_means_normal_operation(self):
        state = maintenance.read_maintenance_state()
        self.assertFalse(state["enabled"])
        self.assertEqual(state["paused_workloads"], [])
        self.assertFalse(self.state_path.exists())

    def test_commands_enable_and_disable_without_reboot(self):
        with patch.object(maintenance, "current_boot_id", return_value="boot-a"):
            active = maintenance.set_maintenance_mode(True, "admin")
            self.assertTrue(active["enabled"])
            self.assertEqual(
                active["paused_workloads"],
                ["host_telemetry", "mqtt_persistence"],
            )
            self.assertTrue(maintenance.maintenance_enabled())

            # Repeating a command is idempotent and does not add audit noise.
            repeated = maintenance.set_maintenance_mode(True, "admin")
            self.assertEqual(repeated, active)
            self.assertEqual(len(self.audit_rows()), 1)

            normal = maintenance.set_maintenance_mode(False, "admin")

        self.assertFalse(normal["enabled"])
        self.assertFalse(maintenance.maintenance_enabled())
        self.assertEqual(len(self.audit_rows()), 2)
        self.assertEqual([row["reason"] for row in self.audit_rows()], ["user", "user"])

    def test_reboot_clears_volatile_mode_and_records_automatic_reset(self):
        with patch.object(maintenance, "current_boot_id", return_value="boot-before"):
            maintenance.set_maintenance_mode(True, "admin")
        self.state_path.unlink()  # /run is a tmpfs, so boot discards its marker.

        with patch.object(maintenance, "current_boot_id", return_value="boot-after"):
            self.assertTrue(maintenance.record_boot_reset())
            self.assertFalse(maintenance.record_boot_reset())

        self.assertFalse(maintenance.maintenance_enabled())
        rows = self.audit_rows()
        self.assertEqual(len(rows), 2)
        self.assertEqual((rows[-1]["actor"], rows[-1]["enabled"], rows[-1]["reason"]),
                         ("system", 0, "boot-reset"))

    def test_corrupt_marker_is_reported_and_collector_fails_open(self):
        self.state_path.parent.mkdir(parents=True)
        self.state_path.write_text("not-json", encoding="utf-8")
        with self.assertRaises(maintenance.MaintenanceStateError):
            maintenance.read_maintenance_state()
        self.assertFalse(maintenance.maintenance_enabled())

    def test_nivus_help_lists_the_supported_maintenance_commands(self):
        cli = Path(__file__).resolve().parents[1] / "deploy" / "nivusctl"
        result = subprocess.run(
            [sys.executable, str(cli), "help"],
            capture_output=True,
            check=False,
            text=True,
            env=os.environ.copy(),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("nivus maintenance status", result.stdout)
        self.assertIn("sudo nivus maintenance enable", result.stdout)
        self.assertIn("sudo nivus maintenance disable", result.stdout)
        self.assertIn("Não é necessário reiniciar", result.stdout)

    def test_nivus_help_can_describe_maintenance_actions(self):
        cli = Path(__file__).resolve().parents[1] / "deploy" / "nivusctl"
        result = subprocess.run(
            [sys.executable, str(cli), "help", "maintenance"],
            capture_output=True,
            check=False,
            text=True,
            env=os.environ.copy(),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Retoma a operação normal sem reiniciar", result.stdout)


if __name__ == "__main__":
    unittest.main()
