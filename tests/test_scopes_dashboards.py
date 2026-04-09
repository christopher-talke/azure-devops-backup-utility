"""Tests for scopes/dashboards.py."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from inventory import Inventory
from paths import BackupPaths
from scopes.dashboards import backup_dashboards


def _make_paths(tmp: Path) -> BackupPaths:
    return BackupPaths(tmp, "https://dev.azure.com/myorg", "20240101T000000Z")


def _make_inv() -> Inventory:
    return Inventory()


DASHBOARD = {"id": "dash-1", "name": "Overview", "widgets": []}
WIDGETS = {"value": [{"id": "w1", "name": "BurndownChart"}]}
NOTIFICATIONS = {"value": [{"id": "n1", "description": "Build failed"}]}


class TestBackupDashboards(unittest.TestCase):
    @patch("azcli.invoke")
    def test_dashboards_and_widgets_exported(self, mock_invoke):
        mock_invoke.side_effect = [
            {"value": [DASHBOARD]},  # dashboards
            WIDGETS,                 # widgets for dash-1
            NOTIFICATIONS,           # notification subscriptions
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_dashboards(bp, inv, "https://dev.azure.com/myorg", "MyProject")

            dash_dir = bp.dashboards_dir("MyProject")
            self.assertTrue((dash_dir / "dashboards.json").exists())
            self.assertTrue((dash_dir / "dashboard_Overview_widgets.json").exists())
            self.assertTrue((dash_dir / "notification_subscriptions.json").exists())

    @patch("azcli.invoke")
    def test_dashboard_content(self, mock_invoke):
        mock_invoke.side_effect = [
            {"value": [DASHBOARD]},
            WIDGETS,
            NOTIFICATIONS,
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_dashboards(bp, inv, "https://dev.azure.com/myorg", "MyProject")

            dash_dir = bp.dashboards_dir("MyProject")
            data = json.loads((dash_dir / "dashboards.json").read_text())
            self.assertEqual(data[0]["name"], "Overview")

            notif = json.loads((dash_dir / "notification_subscriptions.json").read_text())
            self.assertEqual(len(notif), 1)

    @patch("azcli.invoke")
    def test_dry_run_writes_nothing(self, mock_invoke):
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_dashboards(bp, inv, "https://dev.azure.com/myorg", "MyProject",
                              dry_run=True)
            mock_invoke.assert_not_called()

    @patch("azcli.invoke")
    def test_dashboard_failure_records_error(self, mock_invoke):
        mock_invoke.side_effect = RuntimeError("dashboard API unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_dashboards(bp, inv, "https://dev.azure.com/myorg", "MyProject",
                              pat="secret")
            self.assertTrue(len(inv.errors) >= 1)
            self.assertNotIn("secret", inv.errors[0].get("message", ""))

    @patch("azcli.invoke")
    def test_inventory_populated(self, mock_invoke):
        mock_invoke.side_effect = [
            {"value": [DASHBOARD]},
            WIDGETS,
            NOTIFICATIONS,
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_dashboards(bp, inv, "https://dev.azure.com/myorg", "MyProject")
            categories = {e["category"] for e in inv.entries}
            self.assertIn("dashboards", categories)

    @patch("azcli.invoke")
    def test_empty_dashboards(self, mock_invoke):
        mock_invoke.side_effect = [
            {"value": []},     # no dashboards
            NOTIFICATIONS,     # notifications still exported
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_dashboards(bp, inv, "https://dev.azure.com/myorg", "MyProject")
            dash_dir = bp.dashboards_dir("MyProject")
            self.assertTrue((dash_dir / "dashboards.json").exists())
            data = json.loads((dash_dir / "dashboards.json").read_text())
            self.assertEqual(data, [])


if __name__ == "__main__":
    unittest.main()
