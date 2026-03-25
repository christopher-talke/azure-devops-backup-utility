"""Tests for scopes/org.py."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from inventory import Inventory
from paths import BackupPaths
from scopes.org import backup_org


def _make_paths(tmp: Path) -> BackupPaths:
    return BackupPaths(tmp, "https://dev.azure.com/myorg", "20240101T000000Z")


def _make_inv() -> Inventory:
    return Inventory()


class TestBackupOrg(unittest.TestCase):
    @patch("azcli.invoke")
    def test_service_principals_exported(self, mock_invoke):
        """service_principals.json should be written when the endpoint returns data."""
        def side_effect(area, resource, **kwargs):
            if resource == "serviceprincipals":
                return {"value": [{"displayName": "my-sp", "principalName": "sp@tenant"}]}
            if resource == "pats":
                return {"patTokens": []}
            # all other calls return empty
            return {"value": []}

        mock_invoke.side_effect = side_effect

        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_org(bp, inv, "https://dev.azure.com/myorg")

            sp_path = bp.org_file("service_principals.json")
            self.assertTrue(sp_path.exists(), "service_principals.json was not written")
            data = json.loads(sp_path.read_text())
            self.assertIsInstance(data, list)
            self.assertEqual(data[0]["displayName"], "my-sp")

    @patch("azcli.invoke")
    def test_pat_tokens_exported(self, mock_invoke):
        """pat_tokens.json should be written when the endpoint returns data."""
        def side_effect(area, resource, **kwargs):
            if resource == "pats":
                return {"patTokens": [{"displayName": "CI token", "token": "secret123"}]}
            if resource == "serviceprincipals":
                return {"value": []}
            return {"value": []}

        mock_invoke.side_effect = side_effect

        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_org(bp, inv, "https://dev.azure.com/myorg")

            pat_path = bp.org_file("pat_tokens.json")
            self.assertTrue(pat_path.exists(), "pat_tokens.json was not written")
            data = json.loads(pat_path.read_text())
            # token value should be redacted
            self.assertNotEqual(data[0].get("token"), "secret123")

    @patch("azcli.invoke")
    def test_pat_tokens_failure_non_fatal(self, mock_invoke):
        """A failure fetching PAT tokens should not abort the org backup."""
        def side_effect(area, resource, **kwargs):
            if resource == "pats":
                raise RuntimeError("403 Forbidden")
            if resource == "serviceprincipals":
                return {"value": []}
            return {"value": []}

        mock_invoke.side_effect = side_effect

        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            # Should not raise
            backup_org(bp, inv, "https://dev.azure.com/myorg", pat="supersecret")
            # Error recorded but PAT not in message
            pat_errors = [e for e in inv.errors if "pat" in e.get("name", "").lower()]
            self.assertEqual(len(pat_errors), 1)
            self.assertNotIn("supersecret", pat_errors[0].get("message", ""))

    @patch("azcli.invoke")
    def test_dry_run_writes_nothing(self, mock_invoke):
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_org(bp, inv, "https://dev.azure.com/myorg", dry_run=True)
            mock_invoke.assert_not_called()


if __name__ == "__main__":
    unittest.main()
