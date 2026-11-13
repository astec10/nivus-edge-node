import os
from pathlib import Path

import paho.mqtt.client as mqtt


MQTT_BROKER = os.environ.get("NIVUS_MQTT_BROKER", "localhost")
MQTT_PORT = int(os.environ.get("NIVUS_MQTT_PORT", "1883"))


def _mqtt_password():
    password_file = os.environ.get("NIVUS_MQTT_PASSWORD_FILE")
    if password_file:
        return Path(password_file).read_text(encoding="utf-8").strip()
    return os.environ.get("NIVUS_MQTT_PASSWORD")
ALLOWED_MQTT_TOPICS = {
    item.strip()
    for item in os.environ.get(
        "NIVUS_MQTT_ALLOWED_TOPICS", "nivus/edge/relay1"
    ).split(",")
    if item.strip()
}


def publish_mqtt(topic: str, message: str) -> bool:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    loop_started = False
    try:
        mqtt_username = os.environ.get("NIVUS_MQTT_USERNAME")
        mqtt_password = _mqtt_password()
        if mqtt_username:
            client.username_pw_set(mqtt_username, mqtt_password)
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        loop_started = True
        result = client.publish(topic, message, qos=1)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            return False
        result.wait_for_publish(timeout=5)
        return result.is_published()
    except Exception:
        return False
    finally:
        try:
            client.disconnect()
        except Exception:
            pass
        if loop_started:
            client.loop_stop()
