"""Tests for scopes/permissions.py."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from inventory import Inventory
from paths import BackupPaths
from scopes import permissions
from scopes.permissions import backup_permissions, export_security_namespaces_once


def _make_paths(tmp: Path) -> BackupPaths:
    return BackupPaths(tmp, "https://dev.azure.com/myorg", "20240101T000000Z")


def _make_inv() -> Inventory:
    return Inventory()


NAMESPACES = {"value": [{"namespaceId": "ns1", "name": "Git Repositories"}]}
ACLS = {"value": [{"acesDictionary": {"user1": {"allow": 1}}}]}


class TestBackupPermissions(unittest.TestCase):
    def setUp(self):
        # Reset the module-level singleton guard before each test
        permissions._namespaces_exported = False

    @patch("azcli.invoke")
    def test_acl_exported(self, mock_invoke):
        mock_invoke.side_effect = [
            NAMESPACES,  # security namespaces (once)
            ACLS,        # project-level ACLs
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_permissions(bp, inv, "https://dev.azure.com/myorg", "MyProject")

            org_dir = bp.org_file("security_namespaces.json")
            self.assertTrue(org_dir.exists())

            meta_dir = bp.metadata_dir("MyProject")
            self.assertTrue((meta_dir / "permissions_acl.json").exists())

    @patch("azcli.invoke")
    def test_namespaces_exported_once(self, mock_invoke):
        """Security namespaces should only be fetched once across multiple calls."""
        mock_invoke.side_effect = [
            NAMESPACES,  # first call: namespaces
            ACLS,        # first call: ACLs
            ACLS,        # second call: ACLs only (no namespace fetch)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_permissions(bp, inv, "https://dev.azure.com/myorg", "Project1")
            backup_permissions(bp, inv, "https://dev.azure.com/myorg", "Project2")
            # 3 invoke calls total: namespaces + ACLs + ACLs (no second namespace call)
            self.assertEqual(mock_invoke.call_count, 3)

    @patch("azcli.invoke")
    def test_dry_run_writes_nothing(self, mock_invoke):
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_permissions(bp, inv, "https://dev.azure.com/myorg", "MyProject",
                               dry_run=True)
            mock_invoke.assert_not_called()

    @patch("azcli.invoke")
    def test_failure_records_error(self, mock_invoke):
        mock_invoke.side_effect = RuntimeError("permission denied")
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_permissions(bp, inv, "https://dev.azure.com/myorg", "MyProject",
                               pat="secret")
            self.assertTrue(len(inv.errors) >= 1)
            for err in inv.errors:
                self.assertNotIn("secret", err.get("message", ""))

    @patch("azcli.invoke")
    def test_inventory_populated(self, mock_invoke):
        mock_invoke.side_effect = [NAMESPACES, ACLS]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_permissions(bp, inv, "https://dev.azure.com/myorg", "MyProject")
            categories = {e["category"] for e in inv.entries}
            self.assertIn("permissions", categories)


if __name__ == "__main__":
    unittest.main()
