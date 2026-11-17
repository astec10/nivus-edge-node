import jwt
from fastapi import Cookie, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from database import get_db_connection
from security import decode_access_token
from services.auth_sessions import COOKIE_NAME, session_is_active


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token", auto_error=False)


def _load_authenticated_user(token: str | None) -> dict:
    if not token:
        raise HTTPException(status_code=401, detail="Token inválido")
    try:
        payload = decode_access_token(token)
        if (
            not payload.get("sub")
            or payload.get("role") not in {"admin", "viewer"}
            or not payload.get("jti")
            or not session_is_active(payload["jti"], payload["sub"])
        ):
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


def _request_token(token: str | None, session_cookie: str | None) -> str | None:
    return token or session_cookie


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    session_cookie: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> dict:
    payload = _load_authenticated_user(_request_token(token, session_cookie))
    if payload["password_change_required"]:
        raise HTTPException(
            status_code=403,
            detail="Troca de senha obrigatória antes de continuar.",
        )
    return payload


def get_password_change_user(
    token: str | None = Depends(oauth2_scheme),
    session_cookie: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> str:
    payload = _load_authenticated_user(_request_token(token, session_cookie))
    if not payload["password_change_required"] or not payload["_temporary_password_token"]:
        raise HTTPException(
            status_code=403,
            detail="Use a sessão temporária obtida após o login com a senha provisória.",
        )
    return payload["sub"]


def get_current_admin(
    token: str | None = Depends(oauth2_scheme),
    session_cookie: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> str:
    payload = get_current_user(token, session_cookie)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores.")
    return payload["sub"]
