"""Tests for scopes/testplans.py."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from inventory import Inventory
from paths import BackupPaths
from scopes.testplans import backup_testplans


def _make_paths(tmp: Path) -> BackupPaths:
    return BackupPaths(tmp, "https://dev.azure.com/myorg", "20240101T000000Z")


def _make_inv() -> Inventory:
    return Inventory()


PLAN = {"id": "10", "name": "Sprint 1 Tests"}
SUITE = {"id": "20", "name": "Smoke Tests", "planId": "10"}


class TestBackupTestplans(unittest.TestCase):
    @patch("azcli.invoke")
    def test_plans_and_suites_exported(self, mock_invoke):
        mock_invoke.side_effect = [
            {"value": [PLAN]},    # test plans
            {"value": [SUITE]},   # suites for plan 10
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_testplans(bp, inv, "https://dev.azure.com/myorg", "MyProject")

            tp_dir = bp.testplans_dir("MyProject")
            self.assertTrue((tp_dir / "plans.json").exists())
            self.assertTrue((tp_dir / "plan_Sprint_1_Tests_suites.json").exists())

    @patch("azcli.invoke")
    def test_plans_content(self, mock_invoke):
        mock_invoke.side_effect = [
            {"value": [PLAN]},
            {"value": [SUITE]},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_testplans(bp, inv, "https://dev.azure.com/myorg", "MyProject")

            tp_dir = bp.testplans_dir("MyProject")
            plans_data = json.loads((tp_dir / "plans.json").read_text())
            self.assertEqual(plans_data[0]["id"], "10")

    @patch("azcli.invoke")
    def test_suites_content(self, mock_invoke):
        mock_invoke.side_effect = [
            {"value": [PLAN]},
            {"value": [SUITE]},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_testplans(bp, inv, "https://dev.azure.com/myorg", "MyProject")

            tp_dir = bp.testplans_dir("MyProject")
            suites_data = json.loads((tp_dir / "plan_Sprint_1_Tests_suites.json").read_text())
            self.assertEqual(suites_data[0]["name"], "Smoke Tests")

    @patch("azcli.invoke")
    def test_empty_plan_list(self, mock_invoke):
        mock_invoke.side_effect = [{"value": []}]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_testplans(bp, inv, "https://dev.azure.com/myorg", "MyProject")
            tp_dir = bp.testplans_dir("MyProject")
            self.assertTrue((tp_dir / "plans.json").exists())
            mock_invoke.assert_called_once()

    @patch("azcli.invoke")
    def test_suite_failure_records_error(self, mock_invoke):
        mock_invoke.side_effect = [
            {"value": [PLAN]},
            RuntimeError("suites not found"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_testplans(bp, inv, "https://dev.azure.com/myorg", "MyProject",
                              pat="mytoken")
            self.assertEqual(len(inv.errors), 1)
            self.assertNotIn("mytoken", inv.errors[0].get("message", ""))

    @patch("azcli.invoke")
    def test_dry_run_writes_nothing(self, mock_invoke):
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_testplans(bp, inv, "https://dev.azure.com/myorg", "MyProject",
                              dry_run=True)
            mock_invoke.assert_not_called()

    @patch("azcli.invoke")
    def test_inventory_populated(self, mock_invoke):
        mock_invoke.side_effect = [
            {"value": [PLAN]},
            {"value": [SUITE]},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_testplans(bp, inv, "https://dev.azure.com/myorg", "MyProject")
            categories = {e["category"] for e in inv.entries}
            self.assertIn("testplans", categories)


if __name__ == "__main__":
    unittest.main()
