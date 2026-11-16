from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from database import get_db_connection
from security import create_access_token, hash_password, is_password_hash, verify_password


router = APIRouter()


@router.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    username = form_data.username
    if len(username) > 32:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas."
        )

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc)
        cursor.execute(
            "SELECT failures, locked_until FROM login_attempts WHERE username = ?",
            (username,),
        )
        attempt = cursor.fetchone()

        if attempt and attempt["locked_until"]:
            locked_until = datetime.fromisoformat(attempt["locked_until"])
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            if now < locked_until:
                remaining_mins = int((locked_until - now).total_seconds() / 60) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        "Conta temporariamente bloqueada por segurança "
                        f"(Brute Force). Tente novamente em {remaining_mins} minutos."
                    ),
                )
            cursor.execute(
                "UPDATE login_attempts SET failures = 0, locked_until = NULL "
                "WHERE username = ?",
                (username,),
            )
            conn.commit()
            attempt = {"failures": 0, "locked_until": None}

        cursor.execute(
            "SELECT username, password, role, must_change_password FROM users WHERE username = ?",
            (username,),
        )
        user = cursor.fetchone()
        valid_password = user is not None and verify_password(
            form_data.password, user["password"]
        )

        if not valid_password:
            # Use one SQLite UPSERT so concurrent failures cannot race between
            # reading and inserting the unique username counter.
            lock_time = now + timedelta(minutes=15)
            cursor.execute(
                """
                INSERT INTO login_attempts (username, failures, locked_until)
                VALUES (?, 1, NULL)
                ON CONFLICT(username) DO UPDATE SET
                    failures = login_attempts.failures + 1,
                    locked_until = CASE
                        WHEN login_attempts.failures + 1 >= 5 THEN ?
                        ELSE login_attempts.locked_until
                    END
                """,
                (username, lock_time.isoformat()),
            )
            conn.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas.",
            )

        if not is_password_hash(user["password"]):
            cursor.execute(
                "UPDATE users SET password = ? WHERE username = ?",
                (hash_password(form_data.password), username),
            )
        cursor.execute("DELETE FROM login_attempts WHERE username = ?", (username,))
        conn.commit()
        password_change_required = bool(user["must_change_password"])
        return {
            "access_token": create_access_token(
                user["username"], user["role"], password_change_required
            ),
            "token_type": "bearer",
            "password_change_required": password_change_required,
        }
    finally:
        conn.close()
