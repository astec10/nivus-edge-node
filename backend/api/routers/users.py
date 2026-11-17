from fastapi import APIRouter, Depends, HTTPException, Response

from api.dependencies import get_current_admin, get_password_change_user
from api.schemas import PasswordChange, PasswordRotation, UserCreate
from database import get_db_connection
from security import hash_password, verify_password
from services.auth_sessions import issue_session, revoke_user_sessions, set_session_cookie


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
            "INSERT INTO users "
            "(username, password, role, must_change_password) VALUES (?, ?, ?, 1)",
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

        must_change_password = int(payload.username != admin_username)
        cursor = conn.execute(
            "UPDATE users SET password = ?, must_change_password = ? WHERE username = ?",
            (hash_password(payload.new_password), must_change_password, payload.username),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Utilizador não encontrado.")
        conn.commit()
        revoke_user_sessions(payload.username)
    finally:
        conn.close()
    return {"status": "success", "message": "Senha alterada com sucesso."}


@router.post("/first-login-password")
def change_temporary_password(
    payload: PasswordRotation,
    response: Response,
    username: str = Depends(get_password_change_user),
):
    conn = get_db_connection()
    try:
        user = conn.execute(
            "SELECT password, role, must_change_password FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if user is None or not user["must_change_password"]:
            raise HTTPException(status_code=403, detail="Troca de senha não está pendente.")
        conn.execute(
            "UPDATE users SET password = ?, must_change_password = 0 WHERE username = ?",
            (hash_password(payload.new_password), username),
        )
        conn.commit()
        revoke_user_sessions(username)
        access_token = issue_session(username, user["role"])
        set_session_cookie(response, access_token)
    finally:
        conn.close()
    return {
        "password_change_required": False,
        "user": {
            "username": username,
            "role": user["role"],
            "password_change_required": False,
        },
    }


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
