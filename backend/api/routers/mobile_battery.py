from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

from api.dependencies import get_current_admin
from services.mobile_battery import (
    MobileBatteryAuthenticationError,
    list_mobile_battery_devices,
    process_mobile_battery_report,
    register_mobile_battery_device,
    revoke_mobile_battery_device,
)


router = APIRouter(prefix="/api/mobile-battery", tags=["mobile battery"])


class MobileBatteryDeviceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=48, pattern=r"^[A-Za-z0-9 _.-]+$")

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Informe o nome do dispositivo.")
        return value


class MobileBatteryReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    battery_percent: StrictInt = Field(ge=0, le=100)
    observed_at: datetime

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("O horário da leitura precisa incluir fuso horário.")
        return value


@router.get("/devices")
def get_devices(admin: str = Depends(get_current_admin)):
    return list_mobile_battery_devices()


@router.post("/devices", status_code=201)
def create_device(
    payload: MobileBatteryDeviceCreate,
    admin: str = Depends(get_current_admin),
):
    try:
        # The raw credential is returned once and is never persisted or logged.
        return register_mobile_battery_device(payload.name)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.delete("/devices/{device_id}")
def delete_device(device_id: str, admin: str = Depends(get_current_admin)):
    if not revoke_mobile_battery_device(device_id):
        raise HTTPException(status_code=404, detail="Dispositivo ativo não encontrado.")
    return {"status": "revoked", "device_id": device_id}


@router.post("/report", status_code=202)
def receive_report(
    payload: MobileBatteryReport,
    device_token: str = Header(
        ...,
        alias="X-Nivus-Device-Token",
        min_length=40,
        max_length=128,
    ),
):
    try:
        return process_mobile_battery_report(
            device_token, payload.battery_percent, payload.observed_at
        )
    except MobileBatteryAuthenticationError:
        raise HTTPException(status_code=401, detail="Credencial do dispositivo inválida ou revogada.")
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
