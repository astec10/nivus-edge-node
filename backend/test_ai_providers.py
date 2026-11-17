import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
from api.schemas import AIProviderCreate
from pydantic import SecretStr
from services import ai_providers


class ProviderSecretTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.db_patch = patch.object(database, "DB_PATH", self.root / "nivus.db")
        self.key_patch = patch.object(ai_providers, "KEY_FILE", self.root / "provider.key")
        self.db_patch.start()
        self.key_patch.start()
        ai_providers.KEY_FILE.write_bytes(b"K" * 32)
        database.init_db()

    def tearDown(self):
        self.key_patch.stop()
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def create_payload(self, **overrides):
        values = {
            "provider_type": "openai",
            "name": "OpenAI",
            "protocol": "openai-compatible",
            "endpoint_scope": "cloud",
            "base_url": "https://api.openai.com/v1",
            "model_name": "example-model",
            "responsible": "development",
            "purpose": "public synthetic code tasks",
            "auth_method": "bearer",
            "api_key": SecretStr("sk-test-secret-value"),
            "monthly_budget_usd": 5,
            "allowed_data_classes": ["public", "synthetic"],
        }
        values.update(overrides)
        return AIProviderCreate(**values)

    def test_credential_is_encrypted_and_never_in_public_record_or_audit(self):
        public = ai_providers.create_connection(self.create_payload(), "admin")
        self.assertTrue(public["credential_configured"])
        self.assertNotIn("api_key", public)
        self.assertNotIn("credential_ciphertext", public)
        self.assertNotIn("sk-test-secret-value", repr(public))

        conn = database.get_db_connection()
        try:
            row = conn.execute(
                "SELECT credential_ciphertext FROM ai_provider_connections WHERE id=?",
                (public["id"],),
            ).fetchone()
            audit = conn.execute("SELECT action, outcome FROM ai_provider_audit").fetchall()
        finally:
            conn.close()
        self.assertNotIn("sk-test-secret-value", row["credential_ciphertext"])
        self.assertEqual(
            ai_providers.decrypt_credential(public["id"], row["credential_ciphertext"]),
            "sk-test-secret-value",
        )
        self.assertEqual([(item["action"], item["outcome"]) for item in audit], [("created", "ok")])

    def test_associated_data_prevents_moving_ciphertext_to_another_provider_id(self):
        encrypted = ai_providers.encrypt_credential("a" * 32, "secret")
        with self.assertRaises(ai_providers.ProviderSecretError):
            ai_providers.decrypt_credential("b" * 32, encrypted)

    def test_cloud_connection_cannot_be_given_private_data_classes(self):
        with self.assertRaisesRegex(ValueError, "somente dados públicos ou sintéticos"):
            ai_providers.create_connection(
                self.create_payload(allowed_data_classes=["public", "home"]), "admin"
            )

    def test_test_is_explicit_and_only_records_sanitized_result(self):
        provider = ai_providers.create_connection(self.create_payload(), "admin")
        outcome = {
            "success": True,
            "status": "success",
            "http_status": 200,
            "model_count": 1,
            "message": "Conexão confirmada. Nenhum prompt foi enviado.",
        }
        with patch.object(ai_providers, "probe_connection", return_value=outcome) as probe:
            result = ai_providers.test_connection(provider["id"], "admin")
        probe.assert_called_once()
        self.assertEqual(result["status"], "success")
        enabled = ai_providers.set_enabled(provider["id"], True, "admin")
        self.assertTrue(enabled["enabled"])
        self.assertNotIn("credential_ciphertext", enabled)

    def test_cloud_endpoint_rejects_private_or_metadata_addresses(self):
        private_answer = [(2, 1, 6, "", ("169.254.169.254", 443))]
        with patch.object(ai_providers.socket, "getaddrinfo", return_value=private_answer):
            with self.assertRaisesRegex(ValueError, "não público"):
                ai_providers._resolve_pinned_address("example.invalid", 443, "cloud")

    def test_local_probe_rejects_loopback(self):
        loopback_answer = [(2, 1, 6, "", ("127.0.0.1", 11434))]
        with patch.object(ai_providers.socket, "getaddrinfo", return_value=loopback_answer):
            with self.assertRaisesRegex(ValueError, "endereços privados permitidos"):
                ai_providers._resolve_pinned_address("localhost", 11434, "local")


if __name__ == "__main__":
    unittest.main()
