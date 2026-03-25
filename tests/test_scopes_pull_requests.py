"""Tests for scopes/pull_requests.py."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from inventory import Inventory
from paths import BackupPaths
from scopes.pull_requests import backup_pull_requests


def _make_paths(tmp: Path) -> BackupPaths:
    return BackupPaths(tmp, "https://dev.azure.com/myorg", "20240101T000000Z")


def _make_inv() -> Inventory:
    return Inventory()


REPO = {"id": "repo-1", "name": "MyRepo"}
PR = {"pullRequestId": 42, "creationDate": "2024-01-01T00:00:00Z", "closedDate": ""}
THREADS = {"value": [{"id": 1, "comments": []}]}
WORK_ITEMS = {"value": [{"id": 100}]}
LABELS = {"value": [{"name": "bug"}]}
ITERATIONS = {"value": [{"id": 1, "description": "First iteration"}]}


class TestBackupPullRequests(unittest.TestCase):
    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_exports_prs_and_sub_resources(self, mock_az, mock_invoke):
        """PRs, threads, work items, labels, and iterations are all written."""
        mock_az.return_value = [REPO]
        mock_invoke.side_effect = [
            {"value": [PR]},   # pullRequests
            THREADS,           # threads
            WORK_ITEMS,        # pullRequestWorkItems
            LABELS,            # pullRequestLabels
            ITERATIONS,        # pullRequestIterations
        ]

        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_pull_requests(bp, inv, "https://dev.azure.com/myorg", "MyProject")

            pr_dir = bp.pull_requests_dir("MyProject") / "MyRepo"
            self.assertTrue((pr_dir / "pull_requests.json").exists())
            self.assertTrue((pr_dir / "42" / "threads.json").exists())
            self.assertTrue((pr_dir / "42" / "work_items.json").exists())
            self.assertTrue((pr_dir / "42" / "labels.json").exists())
            self.assertTrue((pr_dir / "42" / "iterations.json").exists())

    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_dry_run_writes_nothing(self, mock_az, mock_invoke):
        mock_az.return_value = [REPO]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_pull_requests(bp, inv, "https://dev.azure.com/myorg", "MyProject",
                                  dry_run=True)
            mock_az.assert_not_called()
            mock_invoke.assert_not_called()

    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_labels_content_written_correctly(self, mock_az, mock_invoke):
        mock_az.return_value = [REPO]
        mock_invoke.side_effect = [
            {"value": [PR]},
            THREADS,
            WORK_ITEMS,
            LABELS,
            ITERATIONS,
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_pull_requests(bp, inv, "https://dev.azure.com/myorg", "MyProject")
            labels_path = bp.pull_requests_dir("MyProject") / "MyRepo" / "42" / "labels.json"
            data = json.loads(labels_path.read_text())
            self.assertEqual(data, [{"name": "bug"}])

    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_repo_list_failure_records_error(self, mock_az, mock_invoke):
        mock_az.side_effect = RuntimeError("network error")
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_pull_requests(bp, inv, "https://dev.azure.com/myorg", "MyProject",
                                  pat="mytoken")
            self.assertEqual(len(inv.errors), 1)
            self.assertNotIn("mytoken", inv.errors[0].get("message", ""))


if __name__ == "__main__":
    unittest.main()
