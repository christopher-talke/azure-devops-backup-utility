"""Tests for scopes/wikis.py."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from inventory import Inventory
from paths import BackupPaths
from scopes.wikis import backup_wikis


def _make_paths(tmp: Path) -> BackupPaths:
    return BackupPaths(tmp, "https://dev.azure.com/myorg", "20240101T000000Z")


def _make_inv() -> Inventory:
    return Inventory()


WIKI = {"id": "wiki-1", "name": "MyWiki", "type": "projectWiki"}
PAGES = {"id": 1, "path": "/", "content": "# Home", "subPages": []}


class TestBackupWikis(unittest.TestCase):
    @patch("azcli.invoke")
    def test_wiki_list_and_pages_exported(self, mock_invoke):
        mock_invoke.side_effect = [
            {"value": [WIKI]},   # wikis
            PAGES,               # pages for wiki-1
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_wikis(bp, inv, "https://dev.azure.com/myorg", "MyProject")

            wiki_dir = bp.wikis_dir("MyProject")
            self.assertTrue((wiki_dir / "wikis.json").exists())
            self.assertTrue((wiki_dir / "wiki_MyWiki_pages.json").exists())

    @patch("azcli.invoke")
    def test_wikis_content(self, mock_invoke):
        mock_invoke.side_effect = [
            {"value": [WIKI]},
            PAGES,
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_wikis(bp, inv, "https://dev.azure.com/myorg", "MyProject")

            wiki_dir = bp.wikis_dir("MyProject")
            wikis_data = json.loads((wiki_dir / "wikis.json").read_text())
            self.assertEqual(wikis_data[0]["name"], "MyWiki")

            pages_data = json.loads((wiki_dir / "wiki_MyWiki_pages.json").read_text())
            self.assertEqual(pages_data["path"], "/")

    @patch("azcli.invoke")
    def test_empty_wiki_list(self, mock_invoke):
        """No pages export when there are no wikis."""
        mock_invoke.side_effect = [{"value": []}]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_wikis(bp, inv, "https://dev.azure.com/myorg", "MyProject")
            wiki_dir = bp.wikis_dir("MyProject")
            self.assertTrue((wiki_dir / "wikis.json").exists())
            # only one invoke call (no pages calls)
            mock_invoke.assert_called_once()

    @patch("azcli.invoke")
    def test_page_failure_records_error(self, mock_invoke):
        mock_invoke.side_effect = [
            {"value": [WIKI]},
            RuntimeError("pages endpoint unavailable"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_wikis(bp, inv, "https://dev.azure.com/myorg", "MyProject",
                          pat="secret")
            self.assertEqual(len(inv.errors), 1)
            self.assertNotIn("secret", inv.errors[0].get("message", ""))

    @patch("azcli.invoke")
    def test_dry_run_writes_nothing(self, mock_invoke):
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_wikis(bp, inv, "https://dev.azure.com/myorg", "MyProject",
                          dry_run=True)
            mock_invoke.assert_not_called()

    @patch("azcli.invoke")
    def test_inventory_populated(self, mock_invoke):
        mock_invoke.side_effect = [
            {"value": [WIKI]},
            PAGES,
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_wikis(bp, inv, "https://dev.azure.com/myorg", "MyProject")
            categories = {e["category"] for e in inv.entries}
            self.assertIn("wikis", categories)


if __name__ == "__main__":
    unittest.main()
