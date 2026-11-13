from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_current_admin
from api.schemas import PasswordChange, UserCreate
from database import get_db_connection
from security import hash_password, verify_password


router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("")
def list_users(admin: str = Depends(get_current_admin)):
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT username, role FROM users ORDER BY username"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


@router.post("")
def create_or_update_user(
    payload: UserCreate, admin: str = Depends(get_current_admin)
):
    conn = get_db_connection()
    try:
        exists = conn.execute(
            "SELECT username FROM users WHERE username = ?", (payload.username,)
        ).fetchone()
        if exists is not None:
            raise HTTPException(status_code=409, detail="Este utilizador já existe.")
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (payload.username, hash_password(payload.password), payload.role),
        )
        conn.commit()
    finally:
        conn.close()
    return {"status": "success"}


@router.post("/change-password")
def change_user_password(
    payload: PasswordChange,
    admin_username: str = Depends(get_current_admin),
):
    conn = get_db_connection()
    try:
        admin_record = conn.execute(
            'SELECT password FROM users WHERE username = ? AND role = "admin"',
            (admin_username,),
        ).fetchone()
        if not admin_record or not verify_password(
            payload.admin_password, admin_record["password"]
        ):
            raise HTTPException(
                status_code=401, detail="Senha de Administrador incorreta."
            )

        cursor = conn.execute(
            "UPDATE users SET password = ? WHERE username = ?",
            (hash_password(payload.new_password), payload.username),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Utilizador não encontrado.")
        conn.commit()
    finally:
        conn.close()
    return {"status": "success", "message": "Senha alterada com sucesso."}


@router.delete("/{username}")
def delete_user(username: str, admin: str = Depends(get_current_admin)):
    if username == admin:
        raise HTTPException(
            status_code=400, detail="Não é possível remover a própria conta."
        )

    conn = get_db_connection()
    try:
        target = conn.execute(
            "SELECT role FROM users WHERE username = ?", (username,)
        ).fetchone()
        if target and target["role"] == "admin":
            admin_count = conn.execute(
                'SELECT COUNT(*) AS count FROM users WHERE role = "admin"'
            ).fetchone()["count"]
            if admin_count <= 1:
                raise HTTPException(
                    status_code=400,
                    detail="Não é possível remover o último administrador.",
                )
        conn.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
    finally:
        conn.close()
    return {"status": "success"}
