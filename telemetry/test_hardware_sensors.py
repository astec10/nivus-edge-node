import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

try:
    import psutil
except ImportError:
    psutil = SimpleNamespace(
        Error=Exception,
        sensors_temperatures=lambda fahrenheit=False: {},
        sensors_battery=lambda: None,
    )
    sys.modules["psutil"] = psutil

from hardware_sensors import get_host_battery_metrics, get_thermal_metrics


def sensor(value, label):
    return SimpleNamespace(current=value, label=label)


class HardwareSensorTests(unittest.TestCase):
    @patch("hardware_sensors.psutil.sensors_temperatures")
    def test_prefers_identified_cpu_package_over_generic_acpi(self, read_sensors):
        read_sensors.return_value = {
            "acpitz": [sensor(29.8, "")],
            "coretemp": [sensor(54.0, "Core 0"), sensor(57.0, "Package id 0")],
        }

        metrics = get_thermal_metrics()

        self.assertEqual(metrics["temperature"], 57.0)
        self.assertEqual(metrics["temperature_source"], "coretemp: Package id 0")
        self.assertIsNone(metrics["cpu_hotspot_temperature"])
        self.assertIsNone(metrics["motherboard_temperature"])
        self.assertIsNone(metrics["gpu_temperature"])
        self.assertIsNone(metrics["gpu_hotspot_temperature"])

    @patch("hardware_sensors.psutil.sensors_temperatures")
    def test_exposes_cpu_hotspot_only_when_driver_labels_it_explicitly(self, read_sensors):
        read_sensors.return_value = {
            "coretemp": [
                sensor(56.0, "Package id 0"),
                sensor(79.0, "CPU hotspot"),
            ]
        }

        metrics = get_thermal_metrics()

        self.assertEqual(metrics["temperature"], 56.0)
        self.assertEqual(metrics["cpu_hotspot_temperature"], 79.0)
        self.assertEqual(metrics["cpu_hotspot_source"], "coretemp: CPU hotspot")

    @patch("hardware_sensors.psutil.sensors_temperatures")
    def test_separates_gpu_edge_and_hotspot(self, read_sensors):
        read_sensors.return_value = {
            "amdgpu": [sensor(68.0, "junction"), sensor(47.0, "edge")]
        }

        metrics = get_thermal_metrics()

        self.assertEqual(metrics["gpu_temperature"], 47.0)
        self.assertEqual(metrics["gpu_temperature_source"], "amdgpu: edge")
        self.assertEqual(metrics["gpu_hotspot_temperature"], 68.0)
        self.assertEqual(metrics["gpu_hotspot_source"], "amdgpu: junction")

    @patch("hardware_sensors.psutil.sensors_temperatures")
    def test_accepts_explicit_board_sensor_but_not_acpi_as_board(self, read_sensors):
        read_sensors.return_value = {
            "acpitz": [sensor(29.8, "")],
            "nct6775": [sensor(33.0, "SYSTIN")],
        }

        metrics = get_thermal_metrics()

        self.assertEqual(metrics["motherboard_temperature"], 33.0)
        self.assertEqual(metrics["motherboard_temperature_source"], "nct6775: SYSTIN")
        self.assertIsNone(metrics["temperature"])
        self.assertIsNone(metrics["cpu_hotspot_temperature"])

    @patch("hardware_sensors.psutil.sensors_temperatures")
    def test_psutil_sensor_error_keeps_thermal_metrics_unavailable(self, read_sensors):
        read_sensors.side_effect = psutil.Error("sensor access failed")

        metrics = get_thermal_metrics()

        for key in (
            "temperature",
            "temperature_source",
            "cpu_hotspot_temperature",
            "cpu_hotspot_source",
            "motherboard_temperature",
            "motherboard_temperature_source",
            "gpu_temperature",
            "gpu_temperature_source",
            "gpu_hotspot_temperature",
            "gpu_hotspot_source",
        ):
            self.assertIsNone(metrics[key])

    @patch("hardware_sensors.psutil.sensors_temperatures")
    def test_boolean_temperature_is_not_treated_as_one_degree(self, read_sensors):
        read_sensors.return_value = {"coretemp": [sensor(True, "Package id 0")]}

        metrics = get_thermal_metrics()

        self.assertIsNone(metrics["temperature"])
        self.assertIsNone(metrics["temperature_source"])

    @patch("hardware_sensors.psutil.sensors_battery")
    def test_boolean_battery_percentage_is_not_reported_as_one_percent(self, read_battery):
        read_battery.return_value = SimpleNamespace(percent=True, power_plugged=True)

        metrics = get_host_battery_metrics()

        self.assertIsNone(metrics["host_battery_percent"])
        self.assertIs(metrics["host_battery_power_plugged"], True)
        self.assertIsNone(metrics["host_battery_source"])

    @patch("hardware_sensors.psutil.sensors_temperatures")
    def test_missing_or_implausible_sensors_remain_unavailable(self, read_sensors):
        read_sensors.return_value = {
            "coretemp": [sensor(190.0, "Package id 0")],
            "acpitz": [sensor(29.8, "")],
        }

        metrics = get_thermal_metrics()

        self.assertIsNone(metrics["temperature"])
        self.assertIsNone(metrics["temperature_source"])
        self.assertIsNone(metrics["cpu_hotspot_temperature"])
        self.assertIsNone(metrics["motherboard_temperature"])


if __name__ == "__main__":
    unittest.main()
