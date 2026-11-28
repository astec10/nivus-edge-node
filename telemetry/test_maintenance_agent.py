import unittest
import json
from types import SimpleNamespace
from unittest.mock import call, patch

import agent


class MaintenanceTelemetryAgentTests(unittest.TestCase):
    def test_sampling_pauses_and_resumes_without_restarting_agent(self):
        published = []

        def publish(_topic, payload, **_kwargs):
            published.append(json.loads(payload))
            return SimpleNamespace(
                rc=agent.mqtt.MQTT_ERR_SUCCESS,
                wait_for_publish=lambda **_kwargs: None,
                is_published=lambda: True,
            )

        client = SimpleNamespace(
            username_pw_set=lambda *_args: None,
            connect=lambda *_args: None,
            loop_start=lambda: None,
            loop_stop=lambda: None,
            disconnect=lambda: None,
            publish=publish,
        )

        with (
            patch.object(agent.mqtt, "Client", return_value=client),
            patch.object(agent, "maintenance_enabled", side_effect=[True, False]),
            patch.object(agent.time, "sleep", side_effect=[None, KeyboardInterrupt]),
            patch.object(
                agent.psutil,
                "cpu_percent",
                side_effect=[[0.0, 0.0], 12.5, [10.5, 20.25]],
            ) as cpu,
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

        self.assertEqual(
            cpu.call_args_list,
            [
                call(interval=None, percpu=True),
                call(interval=1),
                call(interval=None, percpu=True),
            ],
        )
        self.assertEqual(len(published), 1)
        self.assertEqual(published[0]["cpu_percent"], 12.5)
        self.assertEqual(published[0]["cpu_per_core_percent"], [10.5, 20.25])
        self.assertEqual(published[0]["cpu_per_core_source"], "psutil.cpu_percent(percpu=True)")
        self.assertEqual(published[0]["cpu_source"], "psutil.cpu_percent")
        self.assertEqual(published[0]["memory_source"], "psutil.virtual_memory")
        self.assertEqual(published[0]["disk_source"], "psutil.disk_usage")

    def test_collect_cpu_usage_rejects_invalid_and_excessive_per_core_values(self):
        with patch.object(
            agent.psutil,
            "cpu_percent",
            side_effect=[[0.0], 12.5, [True, float("nan"), 101.0]],
        ):
            aggregate, per_core, source = agent.collect_cpu_usage()

        self.assertEqual(aggregate, 12.5)
        self.assertEqual(per_core, [None, None, None])
        self.assertIsNone(source)

        with patch.object(
            agent.psutil,
            "cpu_percent",
            side_effect=[[0.0], 12.5, [0.0] * (agent.MAX_LOGICAL_CPUS + 1)],
        ):
            aggregate, per_core, source = agent.collect_cpu_usage()

        self.assertEqual(aggregate, 12.5)
        self.assertIsNone(per_core)
        self.assertIsNone(source)


if __name__ == "__main__":
    unittest.main()
