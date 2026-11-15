from fastapi import APIRouter, Depends, Query

from api.dependencies import get_current_admin, get_current_user
from database import get_db_connection
from services.app_logging import read_application_logs


router = APIRouter(prefix="/api", tags=["telemetry"])


@router.get("/telemetry")
def get_telemetry(
    limit: int = Query(50, ge=1, le=1000),
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM telemetry ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in reversed(rows)]
    finally:
        conn.close()


@router.get("/logs")
def get_system_logs(
    lines: int = Query(25, ge=1, le=100),
    admin: str = Depends(get_current_admin),
):
    return read_application_logs(lines)
