import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from starlette.responses import Response
from unittest.mock import patch

import database
from api.routers import auth


class LoginSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(database, "DB_PATH", Path(self.temp_dir.name) / "nivus.db")
        self.db_patch.start()
        database.init_db()

    def tearDown(self):
        self.db_patch.stop()
        self.temp_dir.cleanup()

    @staticmethod
    def form(username, password):
        return SimpleNamespace(username=username, password=password)

    def test_unknown_username_runs_dummy_password_hash_and_returns_generic_error(self):
        with patch.object(auth, "verify_password", return_value=False) as verify:
            with self.assertRaises(auth.HTTPException) as raised:
                auth.login_for_access_token(Response(), self.form("missing-user", "guess"))

        self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual(raised.exception.detail, "Credenciais inválidas.")
        verify.assert_called_once_with("guess", auth._DUMMY_PASSWORD_HASH)

        conn = database.get_db_connection()
        try:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM login_attempts").fetchone()[0], 0
            )
        finally:
            conn.close()

    def test_account_wide_legacy_lock_does_not_block_login(self):
        conn = database.get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (username, password, role, must_change_password) "
                "VALUES (?, ?, ?, 0)",
                ("admin", "stored-test-hash", "admin"),
            )
            conn.execute(
                "INSERT INTO login_attempts (username, failures, locked_until) "
                "VALUES (?, ?, ?)",
                ("admin", 5, "2999-01-01T00:00:00+00:00"),
            )
            conn.commit()
        finally:
            conn.close()

        with (
            patch.object(auth, "is_password_hash", return_value=True),
            patch.object(auth, "verify_password", return_value=True),
            patch.object(auth, "issue_session", return_value="issued-token"),
            patch.object(auth, "set_session_cookie") as set_cookie,
        ):
            response = auth.login_for_access_token(
                Response(), self.form("admin", "correct")
            )

        self.assertEqual(response["user"]["username"], "admin")
        self.assertEqual(response["password_change_required"], False)
        set_cookie.assert_called_once()
        conn = database.get_db_connection()
        try:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM login_attempts").fetchone()[0], 0
            )
        finally:
            conn.close()

    def test_legacy_password_path_performs_dummy_hash_work(self):
        conn = database.get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (username, password, role, must_change_password) "
                "VALUES (?, ?, ?, 0)",
                ("legacy", "old-plain-password", "viewer"),
            )
            conn.commit()
        finally:
            conn.close()

        with patch.object(auth, "verify_password", return_value=False) as verify:
            with self.assertRaises(auth.HTTPException):
                auth.login_for_access_token(Response(), self.form("legacy", "wrong"))

        self.assertEqual(verify.call_count, 2)
        self.assertEqual(verify.call_args_list[0].args[1], auth._DUMMY_PASSWORD_HASH)
        self.assertEqual(verify.call_args_list[1].args[1], "old-plain-password")


if __name__ == "__main__":
    unittest.main()
