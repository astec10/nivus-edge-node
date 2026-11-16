import getpass
import re
import sqlite3

from database import get_db_connection, init_db
from security import hash_password


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,32}$")
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 256


def main() -> None:
    init_db()
    while True:
        username = input("Nome do primeiro administrador: ").strip()
        if not USERNAME_PATTERN.fullmatch(username):
            print("Use 1–32 caracteres: letras, números, ponto, hífen ou sublinhado.")
            continue

        password = getpass.getpass("Senha temporária (mínimo 8, com letra e número): ")
        confirmation = getpass.getpass("Confirme a senha: ")
        if password != confirmation:
            print("As senhas não coincidem. Tente novamente.")
            continue
        if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
            print("A senha deve ter entre 8 e 256 caracteres. Tente novamente.")
            continue
        if not any(character.isalpha() for character in password) or not any(
            character.isdigit() for character in password
        ):
            print("A senha precisa conter pelo menos uma letra e um número.")
            continue
        break

    conn = get_db_connection()
    try:
        if conn.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            raise SystemExit("Já existem usuários. O provisionamento inicial foi bloqueado.")
        conn.execute(
            "INSERT INTO users "
            "(username, password, role, must_change_password) VALUES (?, ?, 'admin', 1)",
            (username, hash_password(password)),
        )
        conn.commit()
        print("Administrador criado. A senha temporária foi salva somente como hash; será obrigatória a troca no primeiro login.")
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise SystemExit("Não foi possível criar o administrador.") from exc
    finally:
        conn.close()


if __name__ == "__main__":
    main()
