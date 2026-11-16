import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from database import get_db_connection
from security import decode_access_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


def _load_authenticated_user(token: str) -> dict:
    try:
        payload = decode_access_token(token)
        if not payload.get("sub") or payload.get("role") not in {"admin", "viewer"}:
            raise HTTPException(status_code=401, detail="Token inválido")

        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT role, must_change_password FROM users WHERE username = ?",
                (payload["sub"],),
            ).fetchone()
        finally:
            conn.close()

        if row is None or row["role"] != payload["role"]:
            raise HTTPException(status_code=401, detail="Token inválido")
        temporary_password_token = payload.get("password_change_required") is True
        payload["password_change_required"] = bool(row["must_change_password"]) or temporary_password_token
        payload["_temporary_password_token"] = temporary_password_token
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido")


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = _load_authenticated_user(token)
    if payload["password_change_required"]:
        raise HTTPException(
            status_code=403,
            detail="Troca de senha obrigatória antes de continuar.",
        )
    return payload


def get_password_change_user(token: str = Depends(oauth2_scheme)) -> str:
    payload = _load_authenticated_user(token)
    if not payload["password_change_required"] or not payload["_temporary_password_token"]:
        raise HTTPException(
            status_code=403,
            detail="Use a sessão temporária obtida após o login com a senha provisória.",
        )
    return payload["sub"]


def get_current_admin(token: str = Depends(oauth2_scheme)) -> str:
    payload = get_current_user(token)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores.")
    return payload["sub"]
