"""Tests for scopes/boards.py."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from inventory import Inventory
from paths import BackupPaths
from scopes.boards import backup_boards


def _make_paths(tmp: Path) -> BackupPaths:
    return BackupPaths(tmp, "https://dev.azure.com/myorg", "20240101T000000Z")


def _make_inv() -> Inventory:
    return Inventory()


WI_WITH_ATTACHMENT = {
    "id": 1,
    "fields": {"System.Title": "Bug"},
    "relations": [
        {
            "rel": "AttachedFile",
            "url": "https://dev.azure.com/myorg/_apis/wit/attachments/abc123",
            "attributes": {"name": "screenshot.png"},
        }
    ],
}

WI_NO_ATTACHMENT = {"id": 2, "fields": {"System.Title": "Task"}, "relations": []}


class TestBackupBoards(unittest.TestCase):
    @patch("azcli.download_binary")
    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_work_item_attachments_downloaded(self, mock_az, mock_invoke, mock_download):
        """Work items with AttachedFile relations should trigger download_binary."""
        mock_az.side_effect = [
            # wit queries (work item IDs)
            [{"id": 1}],
        ]
        mock_invoke.side_effect = [
            # queries
            {"value": []},
            # tags
            {"value": []},
            # work item 1 fetch (per-item invoke)
            WI_WITH_ATTACHMENT,
            # revisions for WI 1
            {"value": []},
            # board config
            {"value": []},
            # team settings
            {},
            # team iterations
            {"value": []},
        ]

        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_boards(bp, inv, "https://dev.azure.com/myorg", "MyProject")
            mock_download.assert_called_once()
            call_args = mock_download.call_args
            self.assertIn("abc123", call_args[0][0])
            dest_path: Path = call_args[0][1]
            self.assertEqual(dest_path.name, "screenshot.png")

    @patch("azcli.download_binary")
    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_no_attachment_no_download(self, mock_az, mock_invoke, mock_download):
        mock_az.side_effect = [
            [{"id": 2}],
        ]
        mock_invoke.side_effect = [
            {"value": []},   # queries
            {"value": []},   # tags
            WI_NO_ATTACHMENT,  # work item 2 fetch (per-item invoke)
            {"value": []},   # revisions
            {"value": []},   # board config
            {},              # team settings
            {"value": []},   # team iterations
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_boards(bp, inv, "https://dev.azure.com/myorg", "MyProject")
            mock_download.assert_not_called()

    @patch("azcli.download_binary")
    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_revision_history_written(self, mock_az, mock_invoke, mock_download):
        """Revision history file should be written next to work item json."""
        revisions = [{"rev": 1, "fields": {"System.Title": "v1"}}]
        mock_az.side_effect = [
            [{"id": 2}],
        ]
        mock_invoke.side_effect = [
            {"value": []},         # queries
            {"value": []},         # tags
            WI_NO_ATTACHMENT,      # work item 2 fetch (per-item invoke)
            {"value": revisions},  # revisions for WI 2
            {"value": []},         # board config
            {},                    # team settings
            {"value": []},         # team iterations
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_boards(bp, inv, "https://dev.azure.com/myorg", "MyProject")
            wi_dir = bp.work_items_dir("MyProject")
            self.assertTrue((wi_dir / "2_revisions.json").exists())
            data = json.loads((wi_dir / "2_revisions.json").read_text())
            self.assertEqual(data[0]["rev"], 1)

    @patch("azcli.download_binary")
    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_dry_run_writes_nothing(self, mock_az, mock_invoke, mock_download):
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_boards(bp, inv, "https://dev.azure.com/myorg", "MyProject",
                           dry_run=True)
            mock_az.assert_not_called()
            mock_invoke.assert_not_called()
            mock_download.assert_not_called()


if __name__ == "__main__":
    unittest.main()
