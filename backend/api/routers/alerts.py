from fastapi import APIRouter, Depends, Query

from api.dependencies import get_current_user
from database import get_db_connection


router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("/history")
def get_alerts_history(
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM alerts_history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
