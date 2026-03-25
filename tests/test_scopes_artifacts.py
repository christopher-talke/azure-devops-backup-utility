"""Tests for scopes/artifacts.py."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from inventory import Inventory
from paths import BackupPaths
from scopes.artifacts import backup_artifacts


def _make_paths(tmp: Path) -> BackupPaths:
    return BackupPaths(tmp, "https://dev.azure.com/myorg", "20240101T000000Z")


FEED = {"id": "feed-1", "name": "MyFeed"}
PACKAGES = {"value": [{"name": "pkg-a", "version": "1.0.0"}]}
PERMISSIONS = {"value": [{"role": "reader", "identity": "user@example.com"}]}
RETENTION = {"countLimit": 10, "daysToKeepRecentlyDownloadedPackages": 30}


class TestBackupArtifacts(unittest.TestCase):
    @patch("azcli.invoke")
    def test_exports_feeds_packages_permissions_retention(self, mock_invoke):
        mock_invoke.side_effect = [
            {"value": [FEED]},   # feeds
            PACKAGES,            # packages
            PERMISSIONS,         # feedpermissions
            RETENTION,           # retentionpolicies
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_artifacts(bp, inv, "https://dev.azure.com/myorg", "MyProject")

            art_dir = bp.artifacts_dir("MyProject")
            self.assertTrue((art_dir / "feeds.json").exists())
            self.assertTrue((art_dir / "feed_MyFeed_packages.json").exists())
            self.assertTrue((art_dir / "feed_MyFeed_permissions.json").exists())
            self.assertTrue((art_dir / "feed_MyFeed_retention.json").exists())

    @patch("azcli.invoke")
    def test_permissions_content(self, mock_invoke):
        mock_invoke.side_effect = [
            {"value": [FEED]},
            PACKAGES,
            PERMISSIONS,
            RETENTION,
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_artifacts(bp, inv, "https://dev.azure.com/myorg", "MyProject")

            art_dir = bp.artifacts_dir("MyProject")
            data = json.loads((art_dir / "feed_MyFeed_permissions.json").read_text())
            self.assertEqual(data, [{"role": "reader", "identity": "user@example.com"}])

    @patch("azcli.invoke")
    def test_retention_content(self, mock_invoke):
        mock_invoke.side_effect = [
            {"value": [FEED]},
            PACKAGES,
            PERMISSIONS,
            RETENTION,
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_artifacts(bp, inv, "https://dev.azure.com/myorg", "MyProject")

            art_dir = bp.artifacts_dir("MyProject")
            data = json.loads((art_dir / "feed_MyFeed_retention.json").read_text())
            self.assertEqual(data["countLimit"], 10)

    @patch("azcli.invoke")
    def test_dry_run_writes_nothing(self, mock_invoke):
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_artifacts(bp, inv, "https://dev.azure.com/myorg", "MyProject",
                              dry_run=True)
            mock_invoke.assert_not_called()

    @patch("azcli.invoke")
    def test_permission_failure_records_error(self, mock_invoke):
        mock_invoke.side_effect = [
            {"value": [FEED]},
            PACKAGES,
            RuntimeError("forbidden"),
            RETENTION,
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_artifacts(bp, inv, "https://dev.azure.com/myorg", "MyProject",
                              pat="secret")
            self.assertEqual(len(inv.errors), 1)
            self.assertNotIn("secret", inv.errors[0].get("message", ""))


def _make_inv() -> Inventory:
    return Inventory()


if __name__ == "__main__":
    unittest.main()
