import json
import os
import sys
import time
from pathlib import Path

import paho.mqtt.client as mqtt
import psutil

procfs_path = os.environ.get("NIVUS_PROCFS_PATH")
if procfs_path and psutil.LINUX:
    psutil.PROCFS_PATH = procfs_path

BACKEND_PATH = str(Path(__file__).resolve().parents[1] / "backend")
if BACKEND_PATH not in sys.path:
    sys.path.insert(0, BACKEND_PATH)

MQTT_BROKER = os.environ.get("NIVUS_MQTT_BROKER", "localhost")
MQTT_PORT = int(os.environ.get("NIVUS_MQTT_PORT", "1883"))
DISK_PATH = os.environ.get("NIVUS_DISK_PATH", "/")


def _mqtt_password():
    password_file = os.environ.get("NIVUS_MQTT_PASSWORD_FILE")
    if password_file:
        return Path(password_file).read_text(encoding="utf-8").strip()
    return os.environ.get("NIVUS_MQTT_PASSWORD")
TOPIC = os.environ.get("NIVUS_TELEMETRY_TOPIC", "nivus/edge/telemetry")
NODE_NAME = os.environ.get("NIVUS_NODE_NAME", "nivus-edge-node")
from hardware_sensors import get_thermal_metrics
from services.maintenance import maintenance_enabled


def estimate_power_consumption_watts(cpu_percent):
    """Rough estimate only; this is not a physical power measurement."""
    idle_estimate = 15.0
    cpu_component_estimate = 50.0 * (cpu_percent / 100.0)
    return round(idle_estimate + cpu_component_estimate, 1)


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_username = os.environ.get("NIVUS_MQTT_USERNAME")
    mqtt_password = _mqtt_password()
    if mqtt_username:
        client.username_pw_set(mqtt_username, mqtt_password)

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    print("Agente de telemetria conectado ao broker MQTT.")
    samples = 0
    maintenance_was_enabled = False

    try:
        while True:
            if maintenance_enabled():
                if not maintenance_was_enabled:
                    print("Modo de manutenção ativo; coleta e publicação pausadas.")
                    maintenance_was_enabled = True
                time.sleep(1)
                continue
            if maintenance_was_enabled:
                print("Modo de manutenção desativado; coleta retomada.")
                maintenance_was_enabled = False
            cpu = psutil.cpu_percent(interval=1)
            payload = {
                "node": NODE_NAME,
                "timestamp": int(time.time()),
                "cpu_percent": cpu,
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage(DISK_PATH).percent,
                **get_thermal_metrics(),
                "power_consumption": estimate_power_consumption_watts(cpu),
            }
            info = client.publish(TOPIC, json.dumps(payload), qos=1)
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                print("Falha ao publicar telemetria no MQTT.")
            else:
                info.wait_for_publish(timeout=5)
                if not info.is_published():
                    print("Publicação MQTT não foi confirmada pelo broker.")
            samples += 1
            if samples % 60 == 0:
                print(f"Amostras de telemetria publicadas: {samples}.")
            time.sleep(4)
    except KeyboardInterrupt:
        print("Parando o agente de telemetria.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
