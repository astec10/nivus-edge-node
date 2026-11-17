from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from database import get_db_connection
from security import create_access_token, hash_password, is_password_hash, verify_password


router = APIRouter()

# A valid PBKDF2 hash makes unknown usernames take comparable password-check work.
# The value is generated with a random salt and is never associated with an account.
_DUMMY_PASSWORD_HASH = hash_password("nivus-login-timing-placeholder")


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
        cursor.execute(
            "SELECT username, password, role, must_change_password "
            "FROM users WHERE username = ?",
            (username,),
        )
        user = cursor.fetchone()

        if user is None:
            verify_password(form_data.password, _DUMMY_PASSWORD_HASH)
            valid_password = False
        else:
            stored_password = user["password"]
            if not is_password_hash(stored_password):
                # Legacy plaintext or malformed records still perform PBKDF2 work.
                verify_password(form_data.password, _DUMMY_PASSWORD_HASH)
            valid_password = verify_password(form_data.password, stored_password)

        if not valid_password:
            # Do not lock the account globally: that lets anyone on the LAN deny
            # service to a known username. The reverse proxy applies per-IP limits.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas.",
            )

        if not is_password_hash(user["password"]):
            cursor.execute(
                "UPDATE users SET password = ? WHERE username = ?",
                (hash_password(form_data.password), username),
            )
        # Clears counters left by older releases; they no longer gate login.
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
