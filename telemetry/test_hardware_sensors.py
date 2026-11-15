import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

try:
    import psutil  # noqa: F401
except ImportError:
    sys.modules["psutil"] = SimpleNamespace(
        sensors_temperatures=lambda fahrenheit=False: {}
    )

from hardware_sensors import get_thermal_metrics


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
        self.assertIsNone(metrics["motherboard_temperature"])
        self.assertIsNone(metrics["gpu_temperature"])
        self.assertIsNone(metrics["gpu_hotspot_temperature"])

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

    @patch("hardware_sensors.psutil.sensors_temperatures")
    def test_missing_or_implausible_sensors_remain_unavailable(self, read_sensors):
        read_sensors.return_value = {
            "coretemp": [sensor(190.0, "Package id 0")],
            "acpitz": [sensor(29.8, "")],
        }

        metrics = get_thermal_metrics()

        self.assertIsNone(metrics["temperature"])
        self.assertIsNone(metrics["temperature_source"])
        self.assertIsNone(metrics["motherboard_temperature"])


if __name__ == "__main__":
    unittest.main()
