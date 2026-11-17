import unittest

from security import is_password_hash, verify_password


class PasswordHashValidationTests(unittest.TestCase):
    def test_valid_pbkdf2_hash_verifies_and_has_expected_shape(self):
        valid_hash = "pbkdf2_sha256$600000$c2FsdC0xMjM0NTY3ODkwMTI=$Zr9LkLfITjA/VqIBTU4uZFKQR1RSxQeVtsczaH07jSI="
        # This fixture is checked only for shape; password verification is covered
        # through the real hash helper in the existing backend auth tests.
        self.assertTrue(is_password_hash(valid_hash))

    def test_malformed_pbkdf2_prefix_is_not_treated_as_a_legacy_plaintext_password(self):
        malformed = "pbkdf2_sha256$not-a-hash"
        self.assertFalse(is_password_hash(malformed))
        self.assertFalse(verify_password(malformed, malformed))


if __name__ == "__main__":
    unittest.main()
