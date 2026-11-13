import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from database import get_db_connection
from security import decode_access_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = decode_access_token(token)
        if not payload.get("sub") or payload.get("role") not in {"admin", "viewer"}:
            raise HTTPException(status_code=401, detail="Token inválido")

        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT role FROM users WHERE username = ?", (payload["sub"],)
            ).fetchone()
        finally:
            conn.close()

        if row is None or row["role"] != payload["role"]:
            raise HTTPException(status_code=401, detail="Token inválido")
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido")


def get_current_admin(token: str = Depends(oauth2_scheme)) -> str:
    payload = get_current_user(token)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores.")
    return payload["sub"]
