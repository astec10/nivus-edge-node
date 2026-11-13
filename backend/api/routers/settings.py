from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_current_admin, get_current_user
from api.schemas import SettingUpdate
from database import get_db_connection


router = APIRouter(prefix="/api/settings", tags=["settings"])


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
