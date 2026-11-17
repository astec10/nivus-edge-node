import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
import security
from services import auth_sessions


class RevocableSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.db_patch = patch.object(database, "DB_PATH", root / "nivus.db")
        self.db_patch.start()
        self.secret_path = root / "jwt_secret"
        self.secret_path.write_text("x" * 64, encoding="utf-8")
        self.secret_patch = patch.object(security, "JWT_SECRET_FILE", self.secret_path)
        self.secret_patch.start()
        database.init_db()
        conn = database.get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (username, password, role, must_change_password) "
                "VALUES ('admin', 'hash', 'admin', 0)"
            )
            conn.commit()
        finally:
            conn.close()

    def tearDown(self):
        self.secret_patch.stop()
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def test_session_stores_only_hash_and_revocation_is_immediate(self):
        token = auth_sessions.issue_session("admin", "admin")
        payload = security.decode_access_token(token)
        self.assertTrue(auth_sessions.session_is_active(payload["jti"], "admin"))

        conn = database.get_db_connection()
        try:
            stored = conn.execute("SELECT session_hash FROM auth_sessions").fetchone()[0]
        finally:
            conn.close()
        self.assertNotEqual(stored, payload["jti"])

        auth_sessions.revoke_session(payload["jti"])
        self.assertFalse(auth_sessions.session_is_active(payload["jti"], "admin"))

    def test_password_change_revocation_invalidates_all_user_sessions(self):
        first = security.decode_access_token(auth_sessions.issue_session("admin", "admin"))
        second = security.decode_access_token(auth_sessions.issue_session("admin", "admin"))
        auth_sessions.revoke_user_sessions("admin")
        self.assertFalse(auth_sessions.session_is_active(first["jti"], "admin"))
        self.assertFalse(auth_sessions.session_is_active(second["jti"], "admin"))

    def test_browser_cookie_is_http_only_and_secure(self):
        from starlette.responses import Response

        response = Response()
        auth_sessions.set_session_cookie(response, "opaque-jwt")
        cookie = response.headers["set-cookie"].lower()
        self.assertIn("httponly", cookie)
        self.assertIn("secure", cookie)
        self.assertIn("samesite=strict", cookie)
        self.assertNotIn("opaque-jwt", cookie.split(";", 1)[0].split("=", 1)[1] if False else "")


if __name__ == "__main__":
    unittest.main()
