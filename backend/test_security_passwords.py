import unittest

from security import hash_password, is_password_hash, verify_password


class PasswordHashValidationTests(unittest.TestCase):
    def test_valid_pbkdf2_hash_verifies_and_has_expected_shape(self):
        valid_hash = hash_password("test-password-123")
        self.assertTrue(is_password_hash(valid_hash))
        self.assertTrue(verify_password("test-password-123", valid_hash))
        self.assertFalse(verify_password("wrong-password", valid_hash))

    def test_malformed_pbkdf2_prefix_is_not_treated_as_a_legacy_plaintext_password(self):
        malformed = "pbkdf2_sha256$not-a-hash"
        self.assertFalse(is_password_hash(malformed))
        self.assertFalse(verify_password(malformed, malformed))


if __name__ == "__main__":
    unittest.main()
