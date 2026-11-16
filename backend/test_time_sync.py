import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from api.schemas import TimeSyncUpdate


HELPER_PATH = Path(__file__).resolve().parents[1] / "deploy" / "nivus-timesyncd.py"
SPEC = importlib.util.spec_from_file_location("nivus_timesyncd", HELPER_PATH)
time_sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(time_sync)


class TimeSyncSchemaTests(unittest.TestCase):
    def test_accepts_three_distinct_dns_hosts_and_normalizes_them(self):
        payload = TimeSyncUpdate(servers=["A.NTP.BR.", "b.ntp.br", "c.ntp.br"])
        self.assertEqual(payload.servers, ["a.ntp.br", "b.ntp.br", "c.ntp.br"])

    def test_rejects_wrong_count_duplicates_urls_ports_and_ip_addresses(self):
        for servers in (
            ["a.ntp.br", "b.ntp.br"],
            ["a.ntp.br", "a.ntp.br", "c.ntp.br"],
            ["https://a.ntp.br", "b.ntp.br", "c.ntp.br"],
            ["a.ntp.br:123", "b.ntp.br", "c.ntp.br"],
            ["192.0.2.1", "b.ntp.br", "c.ntp.br"],
        ):
            with self.subTest(servers=servers), self.assertRaises(ValidationError):
                TimeSyncUpdate(servers=servers)


class TimeSyncControllerTests(unittest.TestCase):
    def test_read_acl_only_grants_named_service_user_access(self):
        acl = time_sync._acl_read_only_for_user(12345)
        header = struct.unpack_from("<I", acl, 0)[0]
        entries = [
            struct.unpack_from("<HHI", acl, offset)
            for offset in range(4, len(acl), 8)
        ]
        self.assertEqual(header, 0x0002)
        self.assertEqual(entries[0], (0x01, 0o6, 0xFFFFFFFF))
        self.assertEqual(entries[1], (0x02, 0o4, 12345))
        self.assertEqual(entries[2], (0x04, 0o0, 0xFFFFFFFF))
        self.assertEqual(entries[3], (0x10, 0o4, 0xFFFFFFFF))
        self.assertEqual(entries[4], (0x20, 0o0, 0xFFFFFFFF))

    def test_rejects_ip_addresses_in_privileged_helper(self):
        for address in ("192.0.2.10", "2001:db8::1"):
            with self.subTest(address=address):
                with self.assertRaises(time_sync.TimeSyncError) as caught:
                    time_sync.validate_servers([address, "b.ntp.br", "c.ntp.br"])
                self.assertEqual(caught.exception.code, "invalid_servers")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.config = root / "etc" / "systemd" / "timesyncd.conf.d" / "90-nivus.conf"
        self.backups = root / "var" / "backups" / "time-sync"
        self.latest = self.backups / "latest"
        self.stack = [
            patch.object(time_sync, "CONFIG_PATH", self.config),
            patch.object(time_sync, "BACKUP_ROOT", self.backups),
            patch.object(time_sync, "LATEST_BACKUP_FILE", self.latest),
            patch.object(time_sync, "service_active", side_effect=lambda unit: unit == "systemd-timesyncd.service"),
            patch.object(time_sync, "_ntp_synchronized", return_value=True),
            patch.object(time_sync, "_restart_timesyncd", return_value=True),
            patch.object(time_sync, "_systemd_timesync_uid", return_value=65534),
        ]
        for item in self.stack:
            item.start()
            self.addCleanup(item.stop)

    def tearDown(self):
        self.temp.cleanup()

    def test_applies_three_hosts_and_restores_previous_managed_config(self):
        previous = time_sync.render_config(["old-a.example", "old-b.example", "old-c.example"])
        self.config.parent.mkdir(parents=True)
        self.config.write_bytes(previous)

        applied = time_sync.apply_servers(["a.ntp.br", "b.ntp.br", "c.ntp.br"])
        self.assertEqual(applied["configured_servers"], ["a.ntp.br", "b.ntp.br", "c.ntp.br"])
        self.assertTrue(applied["can_configure"])
        self.assertEqual(self.config.read_bytes(), time_sync.render_config(["a.ntp.br", "b.ntp.br", "c.ntp.br"]))
        self.assertTrue(self.latest.is_file())

        rolled_back = time_sync.rollback_last()
        self.assertEqual(rolled_back["configured_servers"], ["old-a.example", "old-b.example", "old-c.example"])
        self.assertEqual(self.config.read_bytes(), previous)
        self.assertFalse(self.latest.exists())

    def test_rollback_removes_nivus_file_when_there_was_no_previous_file(self):
        self.config.parent.mkdir(parents=True)
        time_sync.apply_servers(["a.ntp.br", "b.ntp.br", "c.ntp.br"])
        time_sync.rollback_last()
        self.assertFalse(self.config.exists())

    def test_rejects_an_existing_unmanaged_drop_in_without_overwriting_it(self):
        self.config.parent.mkdir(parents=True)
        original = b"[Time]\nNTP=ntp.example\n"
        self.config.write_bytes(original)
        with self.assertRaises(time_sync.TimeSyncError) as caught:
            time_sync.apply_servers(["a.ntp.br", "b.ntp.br", "c.ntp.br"])
        self.assertEqual(caught.exception.code, "config_conflict")
        self.assertEqual(self.config.read_bytes(), original)
        self.assertFalse(self.latest.exists())

    def test_does_not_replace_or_configure_another_active_time_client(self):
        with patch.object(time_sync, "service_active", side_effect=lambda unit: unit == "chrony.service"):
            state = time_sync.read_host_status()
            self.assertEqual(state["state"], "managed_elsewhere")
            self.assertFalse(state["can_configure"])
            with self.assertRaises(time_sync.TimeSyncError) as caught:
                time_sync.apply_servers(["a.ntp.br", "b.ntp.br", "c.ntp.br"])
        self.assertEqual(caught.exception.code, "client_conflict")

    def test_failed_restart_restores_previous_config_and_backup_pointer(self):
        previous = time_sync.render_config(["old-a.example", "old-b.example", "old-c.example"])
        self.config.parent.mkdir(parents=True)
        self.config.write_bytes(previous)
        with patch.object(time_sync, "_restart_timesyncd", side_effect=[False, True]):
            with self.assertRaises(time_sync.TimeSyncError) as caught:
                time_sync.apply_servers(["a.ntp.br", "b.ntp.br", "c.ntp.br"])
        self.assertEqual(caught.exception.code, "restart_failed")
        self.assertEqual(self.config.read_bytes(), previous)
        self.assertFalse(self.latest.exists())

    def test_dispatch_rejects_extra_fields(self):
        with self.assertRaises(time_sync.TimeSyncError) as caught:
            time_sync._dispatch({"action": "status", "command": "anything"})
        self.assertEqual(caught.exception.code, "invalid_request")


if __name__ == "__main__":
    unittest.main()
