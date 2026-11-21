import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from power_policy import (
    PowerPolicyError,
    apply_governor,
    apply_policy,
    load_config,
    read_linux_mains,
    read_nut_status,
)


class PowerPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.power_root = self.root / "power_supply"
        self.cpufreq_root = self.root / "cpufreq"
        self.power_root.mkdir()
        self.cpufreq_root.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def _supply(self, name, supply_type, online=None):
        path = self.power_root / name
        path.mkdir()
        (path / "type").write_text(supply_type, encoding="ascii")
        if online is not None:
            (path / "online").write_text(str(online), encoding="ascii")
        return path

    def _cpu_policy(self, name, available="powersave schedutil performance", current="schedutil"):
        path = self.cpufreq_root / name
        path.mkdir()
        (path / "scaling_available_governors").write_text(available, encoding="ascii")
        (path / "scaling_governor").write_text(current, encoding="ascii")
        return path

    def _config(self, source=None, enabled=True):
        return {
            "schema_version": 1,
            "enabled": enabled,
            "source": source or {"type": "linux_mains", "feed_topology": "direct_ac"},
            "governors": {"on_ac": "performance", "conservative": "schedutil"},
        }

    def test_linux_mains_maps_online_and_offline_and_ignores_battery_percent(self):
        self._supply("AC", "Mains", 1)
        self._supply("BAT0", "Battery")
        self.assertEqual(read_linux_mains(self.power_root).state, "ac")
        (self.power_root / "AC" / "online").write_text("0", encoding="ascii")
        self.assertEqual(read_linux_mains(self.power_root).state, "battery")

    def test_missing_or_conflicting_mains_signal_is_unknown(self):
        self.assertEqual(read_linux_mains(self.power_root).state, "unknown")
        self._supply("AC", "Mains", 1)
        self._supply("AC2", "Mains", 0)
        self.assertEqual(read_linux_mains(self.power_root).state, "unknown")

    def test_ups_output_cannot_be_used_as_evidence_of_upstream_ac(self):
        self._supply("AC", "Mains", 1)
        config = self._config({"type": "linux_mains", "feed_topology": "ups_output"})
        self._cpu_policy("policy0")
        result = apply_policy(config, power_supply_root=self.power_root, cpufreq_root=self.cpufreq_root)
        self.assertEqual(result["signal"], "unknown")
        self.assertEqual(result["governor"], "schedutil")

    def test_nut_status_only_accepts_unambiguous_fresh_read(self):
        clock = Mock(return_value=1234.0)
        online = read_nut_status(
            "homeups@localhost",
            runner=Mock(return_value=SimpleNamespace(returncode=0, stdout="OL CHRG\n")),
            clock=clock,
        )
        on_battery = read_nut_status(
            "homeups@localhost",
            runner=Mock(return_value=SimpleNamespace(returncode=0, stdout="OB LB\n")),
            clock=clock,
        )
        stale = read_nut_status(
            "homeups@localhost",
            runner=Mock(return_value=SimpleNamespace(returncode=1, stdout="", stderr="stale")),
            clock=clock,
        )
        ambiguous = read_nut_status(
            "homeups@localhost",
            runner=Mock(return_value=SimpleNamespace(returncode=0, stdout="OL OB\n")),
            clock=clock,
        )
        self.assertEqual((online.state, on_battery.state, stale.state, ambiguous.state),
                         ("ac", "battery", "unknown", "unknown"))
        self.assertEqual(online.observed_at, 1234.0)

    def test_nut_target_is_local_and_invoked_without_a_shell(self):
        runner = Mock(return_value=SimpleNamespace(returncode=0, stdout="OL\n"))
        self.assertEqual(read_nut_status("ups;touch /tmp/x@localhost", runner=runner).state, "unknown")
        runner.assert_not_called()
        self.assertEqual(read_nut_status("ups@localhost", runner=runner).state, "ac")
        self.assertEqual(runner.call_args.args[0], ["/usr/bin/upsc", "ups@localhost", "ups.status"])
        self.assertNotIn("shell", runner.call_args.kwargs)

    def test_power_signal_selects_governor_and_unknown_uses_conservative_profile(self):
        self._cpu_policy("policy0")
        self._supply("AC", "Mains", 1)
        result = apply_policy(self._config(), power_supply_root=self.power_root,
                              cpufreq_root=self.cpufreq_root)
        self.assertEqual(result["governor"], "performance")
        self.assertEqual((self.cpufreq_root / "policy0" / "scaling_governor").read_text().strip(),
                         "performance")
        (self.power_root / "AC" / "online").write_text("invalid", encoding="ascii")
        result = apply_policy(self._config(), power_supply_root=self.power_root,
                              cpufreq_root=self.cpufreq_root)
        self.assertEqual((result["signal"], result["governor"]), ("unknown", "schedutil"))

    def test_unsupported_on_ac_governor_falls_back_to_supported_conservative_profile(self):
        self._cpu_policy("policy0", available="powersave schedutil", current="schedutil")
        self._supply("AC", "Mains", 1)
        result = apply_policy(self._config(), power_supply_root=self.power_root,
                              cpufreq_root=self.cpufreq_root)
        self.assertEqual((result["signal"], result["governor"]), ("unknown", "schedutil"))

    def test_forced_performance_cannot_be_selected_as_conservative_profile(self):
        path = self.root / "policy.json"
        config = self._config()
        config["governors"]["conservative"] = "performance"
        path.write_text(json.dumps(config), encoding="utf-8")
        with self.assertRaises(PowerPolicyError):
            load_config(path, require_root_owner=False)

    def test_unsupported_governor_preflight_writes_nothing(self):
        first = self._cpu_policy("policy0")
        self._cpu_policy("policy1", available="powersave schedutil", current="schedutil")
        with self.assertRaises(PowerPolicyError):
            apply_governor("performance", cpufreq_root=self.cpufreq_root)
        self.assertEqual((first / "scaling_governor").read_text(), "schedutil")

    def test_partial_write_failure_rolls_back_prior_policy(self):
        first = self._cpu_policy("policy0")
        second = self._cpu_policy("policy1")
        original_write_text = Path.write_text

        def fail_second_policy(path, data, *args, **kwargs):
            if path == second / "scaling_governor" and data == "performance\n":
                raise OSError("simulated sysfs failure")
            return original_write_text(path, data, *args, **kwargs)

        with unittest.mock.patch.object(Path, "write_text", new=fail_second_policy):
            with self.assertRaises(PowerPolicyError):
                apply_governor("performance", cpufreq_root=self.cpufreq_root)
        self.assertEqual((first / "scaling_governor").read_text().strip(), "schedutil")
        self.assertEqual((second / "scaling_governor").read_text().strip(), "schedutil")

    def test_disabled_policy_restores_conservative_governor_without_reading_source(self):
        self._cpu_policy("policy0", current="performance")
        result = apply_policy(self._config(enabled=False), power_supply_root=self.power_root,
                              cpufreq_root=self.cpufreq_root)
        self.assertEqual(result["status"], "disabled")
        self.assertEqual(result["governor"], "schedutil")
        self.assertEqual((self.cpufreq_root / "policy0" / "scaling_governor").read_text().strip(),
                         "schedutil")

    def test_config_rejects_nonlocal_nut_target_and_reads_valid_file(self):
        path = self.root / "policy.json"
        invalid = self._config({"type": "nut", "target": "ups@192.168.1.2"})
        path.write_text(json.dumps(invalid), encoding="utf-8")
        with self.assertRaises(PowerPolicyError):
            load_config(path, require_root_owner=False)
        path.write_text(json.dumps(self._config()), encoding="utf-8")
        self.assertTrue(load_config(path, require_root_owner=False)["enabled"])


if __name__ == "__main__":
    unittest.main()
