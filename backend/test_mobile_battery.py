import hashlib
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import database
from api.routers.mobile_battery import MobileBatteryReport
from pydantic import ValidationError
from services import mobile_battery


class MobileBatteryAutomationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(database, "DB_PATH", Path(self.temp_dir.name) / "nivus.db")
        self.db_patch.start()
        database.init_db()
        self.device = mobile_battery.register_mobile_battery_device("Telefone de teste")
        self.token = self.device["token"]
        self.now = datetime(2026, 11, 16, 20, 0, tzinfo=timezone.utc)
        self.publish_patch = patch.object(mobile_battery, "publish_mqtt", return_value=True)
        self.publish = self.publish_patch.start()

    def tearDown(self):
        self.publish_patch.stop()
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def report(self, level, seconds=0, observed_seconds=None):
        offset = seconds if observed_seconds is None else observed_seconds
        return mobile_battery.process_mobile_battery_report(
            self.token, level, self.now + timedelta(seconds=offset),
            now=self.now + timedelta(seconds=seconds),
        )

    def test_threshold_sends_only_one_off_per_low_battery_episode(self):
        first = self.report(20)
        repeated = self.report(19, seconds=60)
        recovered = self.report(21, seconds=120)
        low_again = self.report(20, seconds=180)
        self.assertEqual(first["action"], "OFF")
        self.assertEqual(repeated["reason"], "off_already_sent")
        self.assertEqual(recovered["action"], "none")
        self.assertEqual(low_again["action"], "OFF")
        self.assertEqual(self.publish.call_count, 2)
        self.assertEqual([call.args for call in self.publish.call_args_list],
                         [("nivus/edge/relay1", "OFF")] * 2)
        conn = database.get_db_connection()
        try:
            audit = conn.execute("SELECT command, source FROM actuator_audit ORDER BY id").fetchall()
        finally:
            conn.close()
        self.assertEqual([(row["command"], row["source"]) for row in audit],
                         [("OFF", "mobile_battery"), ("OFF", "mobile_battery")])

    def test_stale_and_future_reports_never_publish(self):
        stale = mobile_battery.process_mobile_battery_report(
            self.token, 10, self.now - timedelta(hours=2), now=self.now
        )
        self.assertEqual(stale["reason"], "stale_reading")
        with self.assertRaises(ValueError):
            mobile_battery.process_mobile_battery_report(
                self.token, 10, self.now + timedelta(minutes=2), now=self.now
            )
        self.publish.assert_not_called()

    def test_out_of_order_report_is_ignored(self):
        self.report(50)
        result = mobile_battery.process_mobile_battery_report(
            self.token, 10, self.now - timedelta(seconds=1),
            now=self.now + timedelta(seconds=10),
        )
        self.assertEqual(result["reason"], "duplicate_or_out_of_order")
        self.publish.assert_not_called()

    def test_failed_publish_has_bounded_retry_and_never_sends_on(self):
        self.publish.return_value = False
        first = self.report(15)
        limited = self.report(14, seconds=60)
        retried = self.report(13, seconds=300)
        self.assertEqual(first["reason"], "broker_unavailable")
        self.assertEqual(limited["reason"], "retry_cooldown")
        self.assertEqual(retried["reason"], "broker_unavailable")
        self.assertEqual(self.publish.call_count, 2)
        self.assertTrue(all(call.args[1] == "OFF" for call in self.publish.call_args_list))

    def test_revoked_device_and_invalid_percent_do_not_publish(self):
        self.assertTrue(mobile_battery.revoke_mobile_battery_device(self.device["device_id"]))
        with self.assertRaises(mobile_battery.MobileBatteryAuthenticationError):
            self.report(10)
        with self.assertRaises(ValidationError):
            MobileBatteryReport.model_validate({
                "battery_percent": 101, "observed_at": self.now.isoformat()
            })
        with self.assertRaises(ValidationError):
            MobileBatteryReport.model_validate({
                "battery_percent": "20", "observed_at": self.now.isoformat()
            })
        self.publish.assert_not_called()

    def test_device_listing_never_exposes_token_or_hash(self):
        devices = mobile_battery.list_mobile_battery_devices()
        self.assertEqual(len(devices), 1)
        self.assertNotIn("token", devices[0])
        self.assertNotIn("token_sha256", devices[0])
        conn = database.get_db_connection()
        try:
            stored = conn.execute(
                "SELECT token_sha256 FROM mobile_battery_devices WHERE device_id = ?",
                (self.device["device_id"],),
            ).fetchone()["token_sha256"]
        finally:
            conn.close()
        self.assertEqual(stored, hashlib.sha256(self.token.encode("utf-8")).hexdigest())
        self.assertNotEqual(stored, self.token)


if __name__ == "__main__":
    unittest.main()
