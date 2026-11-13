import subprocess

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_current_admin, get_current_user
from database import get_db_connection


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
    try:
        result = subprocess.run(
            ["pm2", "logs", "nivus-dashboard", "--lines", str(lines), "--nostream"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        logs_output = result.stdout if result.returncode == 0 else result.stderr
        return {"logs": logs_output.splitlines()[-lines:]}
    except Exception:
        return {"logs": ["Logs indisponíveis no momento."]}
