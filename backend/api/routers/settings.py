import logging

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_current_admin, get_current_user
from api.schemas import SettingUpdate, TimeSyncUpdate
from database import get_db_connection
from services.time_sync import (
    TimeSyncControllerError,
    apply_host_time_sync,
    get_host_time_sync_status,
    rollback_host_time_sync,
)


router = APIRouter(prefix="/api/settings", tags=["settings"])
logger = logging.getLogger("nivus.api.settings")


@router.get("")
def get_settings(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT * FROM system_settings").fetchall()
        return {row["key"]: row["value"] for row in rows}
    finally:
        conn.close()


@router.post("")
def update_setting(
    payload: SettingUpdate, admin: str = Depends(get_current_admin)
):
    try:
        value = float(payload.value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Valor numérico inválido.")
    upper_bound = 150 if payload.key == "temp_threshold" else 100
    if not 0 <= value <= upper_bound:
        raise HTTPException(status_code=422, detail="Valor fora do intervalo permitido.")

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)",
            (payload.key, payload.value),
        )
        conn.commit()
    finally:
        conn.close()
    return {"status": "success"}


@router.get("/time-sync")
def read_host_time_sync(current_user: dict = Depends(get_current_user)):
    return get_host_time_sync_status()


def _raise_time_sync_error(error: TimeSyncControllerError) -> None:
    status_by_code = {
        "invalid_servers": 422,
        "config_conflict": 409,
        "client_conflict": 409,
        "client_unavailable": 409,
        "acl_unavailable": 503,
        "no_rollback": 409,
        "backup_invalid": 409,
        "controller_unavailable": 503,
        "config_unavailable": 503,
        "restart_failed": 503,
        "invalid_response": 502,
        "forbidden": 503,
        "rollback_failed": 500,
    }
    raise HTTPException(
        status_code=status_by_code.get(error.code, 500),
        detail=error.message,
    )


@router.post("/time-sync")
def update_host_time_sync(
    payload: TimeSyncUpdate,
    admin: str = Depends(get_current_admin),
):
    try:
        result = apply_host_time_sync(payload.servers)
    except TimeSyncControllerError as error:
        _raise_time_sync_error(error)
    logger.info("Fontes NTP do host alteradas pelo administrador.")
    return result


@router.post("/time-sync/rollback")
def restore_host_time_sync(admin: str = Depends(get_current_admin)):
    try:
        result = rollback_host_time_sync()
    except TimeSyncControllerError as error:
        _raise_time_sync_error(error)
    logger.warning("Configuração NTP anterior restaurada.")
    return result
