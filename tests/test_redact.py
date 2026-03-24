"""Tests for redaction utilities."""

import unittest

from redact import REDACTED, _SENSITIVE_KEYS_LOWER, redact


class TestRedact(unittest.TestCase):
    def test_redact_password(self):
        data = {"user": "admin", "password": "s3cr3t"}
        result = redact(data)
        self.assertEqual(result["user"], "admin")
        self.assertEqual(result["password"], REDACTED)

    def test_redact_nested(self):
        data = {"config": {"token": "abc123", "name": "test"}}
        result = redact(data)
        self.assertEqual(result["config"]["token"], REDACTED)
        self.assertEqual(result["config"]["name"], "test")

    def test_redact_list(self):
        data = [{"secret": "val1"}, {"name": "safe"}]
        result = redact(data)
        self.assertEqual(result[0]["secret"], REDACTED)
        self.assertEqual(result[1]["name"], "safe")

    def test_redact_authorization_parameters_path(self):
        data = {"authorization": {"parameters": {"key": "value"}, "scheme": "Token"}}
        result = redact(data)
        self.assertEqual(result["authorization"]["parameters"], REDACTED)
        self.assertEqual(result["authorization"]["scheme"], "Token")

    def test_redact_case_insensitive_keys(self):
        data = {"Password": "secret", "TOKEN": "abc", "ApiKey": "key123"}
        result = redact(data)
        self.assertEqual(result["Password"], REDACTED)
        self.assertEqual(result["TOKEN"], REDACTED)
        self.assertEqual(result["ApiKey"], REDACTED)

    def test_redact_preserves_non_sensitive(self):
        data = {"name": "project1", "id": 42, "description": "test"}
        result = redact(data)
        self.assertEqual(result, data)

    def test_redact_empty(self):
        self.assertEqual(redact({}), {})
        self.assertEqual(redact([]), [])

    def test_redact_scalar(self):
        self.assertEqual(redact("hello"), "hello")
        self.assertEqual(redact(42), 42)

    def test_original_unchanged(self):
        data = {"password": "secret"}
        redact(data)
        self.assertEqual(data["password"], "secret")


class TestSensitiveKeysLower(unittest.TestCase):
    def test_pre_computed_set_matches_case_insensitive(self):
        """_SENSITIVE_KEYS_LOWER must catch common variants regardless of case."""
        for key in ("ApiKey", "ACCESSTOKEN", "ConnectionString", "PrivateKey", "SecureFileId"):
            self.assertIn(key.lower(), _SENSITIVE_KEYS_LOWER, f"{key!r} not in _SENSITIVE_KEYS_LOWER")

    def test_no_camel_case_duplicates(self):
        """All entries in _SENSITIVE_KEYS_LOWER must already be lowercase (no duplicates)."""
        for key in _SENSITIVE_KEYS_LOWER:
            self.assertEqual(key, key.lower(), f"{key!r} has uppercase letters")


if __name__ == "__main__":
    unittest.main()
