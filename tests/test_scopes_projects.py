"""Tests for scopes/projects.py."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from inventory import Inventory
from paths import BackupPaths
from scopes.projects import backup_project_metadata, list_projects


def _make_paths(tmp: Path) -> BackupPaths:
    return BackupPaths(tmp, "https://dev.azure.com/myorg", "20240101T000000Z")


def _make_inv() -> Inventory:
    return Inventory()


PROJECT = {"id": "proj-1", "name": "MyProject", "state": "wellFormed"}
TEAMS = {"value": [{"id": "t1", "name": "MyProject Team"}]}
AREAS = {"id": 1, "name": "MyProject", "children": []}
ITERATIONS = {"id": 2, "name": "Sprint 1", "children": []}
ACLS = {"value": [{"acesDictionary": {}}]}


class TestListProjects(unittest.TestCase):
    @patch("azcli.az")
    def test_list_projects_returns_values(self, mock_az):
        mock_az.return_value = {"value": [PROJECT]}
        result = list_projects("https://dev.azure.com/myorg")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "MyProject")

    @patch("azcli.az")
    def test_list_projects_handles_list(self, mock_az):
        mock_az.return_value = [PROJECT]
        result = list_projects("https://dev.azure.com/myorg")
        self.assertEqual(len(result), 1)

    @patch("azcli.az")
    def test_list_projects_handles_empty(self, mock_az):
        mock_az.return_value = {"value": []}
        result = list_projects("https://dev.azure.com/myorg")
        self.assertEqual(result, [])


class TestBackupProjectMetadata(unittest.TestCase):
    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_metadata_exported(self, mock_az, mock_invoke):
        mock_az.return_value = PROJECT
        mock_invoke.side_effect = [
            TEAMS,       # teams
            AREAS,       # areas
            ITERATIONS,  # iterations
            ACLS,        # permissions_acl
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_project_metadata(bp, inv, "https://dev.azure.com/myorg", "MyProject")

            meta_dir = bp.metadata_dir("MyProject")
            self.assertTrue((meta_dir / "project.json").exists())
            self.assertTrue((meta_dir / "teams.json").exists())
            self.assertTrue((meta_dir / "areas.json").exists())
            self.assertTrue((meta_dir / "iterations.json").exists())
            self.assertTrue((meta_dir / "permissions_acl.json").exists())

    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_metadata_content(self, mock_az, mock_invoke):
        mock_az.return_value = PROJECT
        mock_invoke.side_effect = [TEAMS, AREAS, ITERATIONS, ACLS]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_project_metadata(bp, inv, "https://dev.azure.com/myorg", "MyProject")

            meta_dir = bp.metadata_dir("MyProject")
            data = json.loads((meta_dir / "project.json").read_text())
            self.assertEqual(data["name"], "MyProject")

            teams = json.loads((meta_dir / "teams.json").read_text())
            self.assertEqual(len(teams), 1)

    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_dry_run_writes_nothing(self, mock_az, mock_invoke):
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_project_metadata(bp, inv, "https://dev.azure.com/myorg", "MyProject",
                                    dry_run=True)
            mock_az.assert_not_called()
            mock_invoke.assert_not_called()

    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_failure_records_error(self, mock_az, mock_invoke):
        mock_az.side_effect = RuntimeError("project not found")
        mock_invoke.side_effect = [TEAMS, AREAS, ITERATIONS, ACLS]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_project_metadata(bp, inv, "https://dev.azure.com/myorg", "MyProject",
                                    pat="secret")
            self.assertTrue(len(inv.errors) >= 1)
            for err in inv.errors:
                self.assertNotIn("secret", err.get("message", ""))

    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_inventory_populated(self, mock_az, mock_invoke):
        mock_az.return_value = PROJECT
        mock_invoke.side_effect = [TEAMS, AREAS, ITERATIONS, ACLS]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_project_metadata(bp, inv, "https://dev.azure.com/myorg", "MyProject")
            categories = {e["category"] for e in inv.entries}
            self.assertIn("project", categories)


if __name__ == "__main__":
    unittest.main()
