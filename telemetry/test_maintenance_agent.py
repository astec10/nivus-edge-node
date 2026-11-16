import unittest
from types import SimpleNamespace
from unittest.mock import patch

import agent


class MaintenanceTelemetryAgentTests(unittest.TestCase):
    def test_sampling_pauses_and_resumes_without_restarting_agent(self):
        client = SimpleNamespace(
            username_pw_set=lambda *_args: None,
            connect=lambda *_args: None,
            loop_start=lambda: None,
            loop_stop=lambda: None,
            disconnect=lambda: None,
            publish=lambda *_args, **_kwargs: SimpleNamespace(
                rc=agent.mqtt.MQTT_ERR_SUCCESS,
                wait_for_publish=lambda **_kwargs: None,
                is_published=lambda: True,
            ),
        )

        with (
            patch.object(agent.mqtt, "Client", return_value=client),
            patch.object(agent, "maintenance_enabled", side_effect=[True, False]),
            patch.object(agent.time, "sleep", side_effect=[None, KeyboardInterrupt]),
            patch.object(agent.psutil, "cpu_percent", return_value=12.5) as cpu,
            patch.object(agent.psutil, "virtual_memory", return_value=SimpleNamespace(percent=30.0)),
            patch.object(agent.psutil, "disk_usage", return_value=SimpleNamespace(percent=40.0)),
            patch.object(agent, "get_thermal_metrics", return_value={
                "temperature": None,
                "temperature_source": None,
                "cpu_hotspot_temperature": None,
                "cpu_hotspot_source": None,
                "motherboard_temperature": None,
                "motherboard_temperature_source": None,
                "gpu_temperature": None,
                "gpu_temperature_source": None,
                "gpu_hotspot_temperature": None,
                "gpu_hotspot_source": None,
            }),
        ):
            agent.main()

        cpu.assert_called_once_with(interval=1)


if __name__ == "__main__":
    unittest.main()
