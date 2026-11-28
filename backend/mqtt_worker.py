import logging
import json
import math
import os
import sqlite3
from pathlib import Path

import paho.mqtt.client as mqtt

from database import get_db_connection, init_db
from services.app_logging import configure_service_logger
from services.maintenance import maintenance_enabled


logger = logging.getLogger("nivus.worker")

MQTT_BROKER = os.environ.get("NIVUS_MQTT_BROKER", "localhost")
MQTT_PORT = int(os.environ.get("NIVUS_MQTT_PORT", "1883"))
MAX_LOGICAL_CPUS = 256


def _mqtt_password():
    password_file = os.environ.get("NIVUS_MQTT_PASSWORD_FILE")
    if password_file:
        return Path(password_file).read_text(encoding="utf-8").strip()
    return os.environ.get("NIVUS_MQTT_PASSWORD")
TOPIC = os.environ.get("NIVUS_TELEMETRY_TOPIC", "nivus/edge/telemetry")


def on_connect(client, userdata, flags, reason_code, properties=None):
    if getattr(reason_code, "value", reason_code) == 0:
        client.subscribe(TOPIC, qos=1)
        logger.info("Worker MQTT conectado e inscrito no tópico de telemetria.")
    else:
        logger.error("Worker MQTT não conseguiu conectar ao broker.")


def _number(payload, name, minimum, maximum, nullable=False):
    value = payload.get(name)
    if value is None and nullable:
        return None
    if isinstance(value, bool):
        raise ValueError(name)
    value = float(value)
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(name)
    return value


def _source(payload, name):
    value = payload.get(name)
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 128
        or any(ord(character) < 32 for character in value)
    ):
        raise ValueError(name)
    return value


def _cpu_per_core(payload):
    values = payload.get("cpu_per_core_percent")
    if values is None:
        return None
    if not isinstance(values, list) or not 1 <= len(values) <= MAX_LOGICAL_CPUS:
        raise ValueError("cpu_per_core_percent")

    validated = []
    for value in values:
        if value is None:
            validated.append(None)
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("cpu_per_core_percent")
        value = float(value)
        if not math.isfinite(value) or not 0 <= value <= 100:
            raise ValueError("cpu_per_core_percent")
        validated.append(value)
    return json.dumps(validated, separators=(",", ":"))


def on_message(client, userdata, msg):
    if maintenance_enabled():
        return
    conn = None
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        node = payload.get("node")
        if not isinstance(node, str) or not 1 <= len(node) <= 128:
            raise ValueError("node")
        timestamp = int(payload["timestamp"])
        cpu = _number(payload, "cpu_percent", 0, 100)
        cpu_source = _source(payload, "cpu_source")
        cpu_per_core_json = _cpu_per_core(payload)
        cpu_per_core_source = _source(payload, "cpu_per_core_source")
        if cpu_per_core_json is None:
            cpu_per_core_source = None
        memory = _number(payload, "memory_percent", 0, 100)
        memory_source = _source(payload, "memory_source")
        disk = _number(payload, "disk_percent", 0, 100)
        disk_source = _source(payload, "disk_source")
        host_battery_percent = _number(payload, "host_battery_percent", 0, 100, nullable=True)
        host_battery_power_plugged = payload.get("host_battery_power_plugged")
        if host_battery_power_plugged is not None and not isinstance(host_battery_power_plugged, bool):
            raise ValueError("host_battery_power_plugged")
        host_battery_source = payload.get("host_battery_source")
        if host_battery_source is not None and (
            not isinstance(host_battery_source, str)
            or len(host_battery_source) > 128
            or any(ord(character) < 32 for character in host_battery_source)
        ):
            raise ValueError("host_battery_source")
        temperature = _number(payload, "temperature", -40, 150, nullable=True)
        temperature_source = payload.get("temperature_source")
        if temperature_source is not None and (
            not isinstance(temperature_source, str)
            or len(temperature_source) > 128
            or any(ord(character) < 32 for character in temperature_source)
        ):
            raise ValueError("temperature_source")
        cpu_hotspot_temperature = _number(
            payload, "cpu_hotspot_temperature", -40, 150, nullable=True
        )
        cpu_hotspot_source = payload.get("cpu_hotspot_source")
        if cpu_hotspot_source is not None and (
            not isinstance(cpu_hotspot_source, str)
            or len(cpu_hotspot_source) > 128
            or any(ord(character) < 32 for character in cpu_hotspot_source)
        ):
            raise ValueError("cpu_hotspot_source")
        motherboard_temperature = _number(
            payload, "motherboard_temperature", -40, 150, nullable=True
        )
        motherboard_temperature_source = payload.get("motherboard_temperature_source")
        if motherboard_temperature_source is not None and (
            not isinstance(motherboard_temperature_source, str)
            or len(motherboard_temperature_source) > 128
            or any(ord(character) < 32 for character in motherboard_temperature_source)
        ):
            raise ValueError("motherboard_temperature_source")
        gpu_temperature = _number(payload, "gpu_temperature", -40, 150, nullable=True)
        gpu_temperature_source = payload.get("gpu_temperature_source")
        if gpu_temperature_source is not None and (
            not isinstance(gpu_temperature_source, str)
            or len(gpu_temperature_source) > 128
            or any(ord(character) < 32 for character in gpu_temperature_source)
        ):
            raise ValueError("gpu_temperature_source")
        gpu_hotspot_temperature = _number(
            payload, "gpu_hotspot_temperature", -40, 150, nullable=True
        )
        gpu_hotspot_source = payload.get("gpu_hotspot_source")
        if gpu_hotspot_source is not None and (
            not isinstance(gpu_hotspot_source, str)
            or len(gpu_hotspot_source) > 128
            or any(ord(character) < 32 for character in gpu_hotspot_source)
        ):
            raise ValueError("gpu_hotspot_source")
        power = _number(payload, "power_consumption", 0, 1000, nullable=True)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT cpu_percent, temperature FROM telemetry ORDER BY id DESC LIMIT 1"
        )
        previous = cursor.fetchone()
        cursor.execute(
            """INSERT INTO telemetry
               (node, timestamp, cpu_percent, cpu_source, cpu_per_core_json, cpu_per_core_source,
                memory_percent, memory_source, disk_percent, disk_source,
                host_battery_percent, host_battery_power_plugged, host_battery_source, temperature,
                temperature_source, cpu_hotspot_temperature, cpu_hotspot_source,
                motherboard_temperature, motherboard_temperature_source,
                gpu_temperature, gpu_temperature_source,
                gpu_hotspot_temperature, gpu_hotspot_source, power_consumption)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                node,
                timestamp,
                cpu,
                cpu_source,
                cpu_per_core_json,
                cpu_per_core_source,
                memory,
                memory_source,
                disk,
                disk_source,
                host_battery_percent,
                int(host_battery_power_plugged) if host_battery_power_plugged is not None else None,
                host_battery_source,
                temperature,
                temperature_source,
                cpu_hotspot_temperature,
                cpu_hotspot_source,
                motherboard_temperature,
                motherboard_temperature_source,
                gpu_temperature,
                gpu_temperature_source,
                gpu_hotspot_temperature,
                gpu_hotspot_source,
                power,
            ),
        )
        telemetry_id = cursor.lastrowid

        cursor.execute("SELECT key, value FROM system_settings")
        settings = {row["key"]: float(row["value"]) for row in cursor.fetchall()}
        checks = (
            ("TEMPERATURE_HIGH", temperature, settings.get("temp_threshold", 75), "temperature"),
            ("CPU_HIGH", cpu, settings.get("cpu_threshold", 90), "cpu_percent"),
        )
        for alert_type, value, threshold, field in checks:
            if value is None or value <= threshold:
                continue
            was_high = (
                previous is not None
                and previous[field] is not None
                and previous[field] > threshold
            )
            if not was_high:
                cursor.execute(
                    "INSERT OR IGNORE INTO alerts_history "
                    "(alert_type, value, threshold, telemetry_id) VALUES (?, ?, ?, ?)",
                    (alert_type, value, threshold, telemetry_id),
                )
                logger.warning(
                    "Alerta %s: valor %.1f excedeu limite %.1f.",
                    alert_type,
                    value,
                    threshold,
                )
        conn.commit()
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        logger.warning("Mensagem MQTT inválida; amostra descartada.")
    except sqlite3.Error:
        logger.exception("Falha ao gravar a amostra MQTT no SQLite.")
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    logger = configure_service_logger("worker")
    init_db()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_username = os.environ.get("NIVUS_MQTT_USERNAME")
    mqtt_password = _mqtt_password()
    if mqtt_username:
        client.username_pw_set(mqtt_username, mqtt_password)
    client.on_connect = on_connect
    client.on_message = on_message
    logger.info("Iniciando o worker MQTT do Nivus.")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()
