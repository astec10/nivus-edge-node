import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

import database
import mqtt_worker
from api.routers import actuator, settings
from api.schemas import ActuatorCommand, SettingUpdate
from services.app_logging import read_application_logs


class OperationalFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.db_patch = patch.object(database, "DB_PATH", self.db_path)
        self.db_patch.start()
        database.init_db()

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def connection(self):
        return database.get_db_connection()

    def test_zero_temperature_threshold_is_saved_and_generates_one_crossing_alert(self):
        settings.update_setting(SettingUpdate(key="temp_threshold", value="0"), admin="admin")
        self.assertEqual(settings.get_settings(current_user={})["temp_threshold"], "0")

        class Message:
            def __init__(self, timestamp, temperature):
                self.payload = (
                    '{"node":"fixture","timestamp":%d,"cpu_percent":10,'
                    '"memory_percent":20,"disk_percent":30,"temperature":%s,'
                    '"temperature_source":"fixture: cpu","cpu_hotspot_temperature":null,'
                    '"cpu_hotspot_source":null,"motherboard_temperature":null,'
                    '"motherboard_temperature_source":null,"gpu_temperature":null,'
                    '"gpu_temperature_source":null,"gpu_hotspot_temperature":null,'
                    '"gpu_hotspot_source":null,"power_consumption":null}'
                    % (timestamp, temperature)
                ).encode("utf-8")

        mqtt_worker.on_message(None, None, Message(100, 35))
        mqtt_worker.on_message(None, None, Message(105, 37))
        conn = self.connection()
        try:
            alert_count = conn.execute(
                "SELECT COUNT(*) FROM alerts_history WHERE alert_type='TEMPERATURE_HIGH'"
            ).fetchone()[0]
            telemetry_count = conn.execute("SELECT COUNT(*) FROM telemetry").fetchone()[0]
            hotspot = conn.execute(
                "SELECT cpu_hotspot_temperature,cpu_hotspot_source "
                "FROM telemetry ORDER BY id DESC LIMIT 1"
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(telemetry_count, 2)
        self.assertEqual(alert_count, 1)
        self.assertEqual(tuple(hotspot), (None, None))

    def test_mqtt_actuator_audit_states_broker_ack_without_claiming_device_confirmation(self):
        command = ActuatorCommand(topic="nivus/edge/relay1", command="ON")
        with patch.object(actuator, "publish_mqtt", return_value=True):
            result = actuator.send_actuator_command(command, admin="admin")
        self.assertTrue(result["broker_accepted"])
        self.assertFalse(result["device_confirmed"])
        conn = self.connection()
        try:
            row = conn.execute("SELECT topic, command FROM actuator_audit").fetchone()
        finally:
            conn.close()
        self.assertEqual((row["topic"], row["command"]), (command.topic, command.command))

    def test_mqtt_actuator_failure_is_not_audited_as_success(self):
        command = ActuatorCommand(topic="nivus/edge/relay1", command="OFF")
        with patch.object(actuator, "publish_mqtt", return_value=False):
            with self.assertRaises(HTTPException) as raised:
                actuator.send_actuator_command(command, admin="admin")
        self.assertEqual(raised.exception.status_code, 503)
        conn = self.connection()
        try:
            count = conn.execute("SELECT COUNT(*) FROM actuator_audit").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(count, 0)

    def test_logs_are_limited_to_application_log_files(self):
        log_dir = Path(self.temp_dir.name) / "logs"
        log_dir.mkdir()
        (log_dir / "api.log").write_text(
            "2026-01-01T00:00:01+0000 INFO API started\n"
            "2026-01-01T00:00:03+0000 INFO API request\n",
            encoding="utf-8",
        )
        (log_dir / "worker.log").write_text(
            "2026-01-01T00:00:02+0000 INFO MQTT connected\n",
            encoding="utf-8",
        )
        with patch.dict(os.environ, {"NIVUS_LOG_DIR": str(log_dir)}):
            result = read_application_logs(2)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["source"], "Nivus API e worker MQTT")
        self.assertEqual(result["logs"], [
            "[WORKER] 2026-01-01T00:00:02+0000 INFO MQTT connected",
            "[API] 2026-01-01T00:00:03+0000 INFO API request",
        ])


if __name__ == "__main__":
    unittest.main()
