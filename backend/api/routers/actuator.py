from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_current_admin, get_current_user
from api.schemas import ActuatorCommand
from database import get_db_connection
from services.mqtt import ALLOWED_MQTT_TOPICS, publish_mqtt


router = APIRouter(prefix="/api/actuator", tags=["actuator"])


@router.post("/command")
def send_actuator_command(
    payload: ActuatorCommand, admin: str = Depends(get_current_admin)
):
    if payload.topic not in ALLOWED_MQTT_TOPICS:
        raise HTTPException(status_code=400, detail="Tópico MQTT não permitido.")
    if payload.command not in {"ON", "OFF"}:
        raise HTTPException(status_code=400, detail="Comando MQTT não permitido.")
    if not publish_mqtt(payload.topic, payload.command):
        raise HTTPException(
            status_code=503, detail="Broker MQTT não confirmou o comando."
        )

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO actuator_audit (topic, command) VALUES (?, ?)",
            (payload.topic, payload.command),
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "status": "success",
        "broker_accepted": True,
        "device_confirmed": False,
        "message": "O broker MQTT confirmou o recebimento; o dispositivo não confirmou o estado físico.",
    }


@router.get("/audit")
def get_actuator_audit(
    limit: int = Query(15, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM actuator_audit ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
