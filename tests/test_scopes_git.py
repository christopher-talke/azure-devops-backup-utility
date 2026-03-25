"""Tests for scopes/git.py — per-repo permissions export."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from inventory import Inventory
from paths import BackupPaths
from scopes.git import backup_git


def _make_paths(tmp: Path) -> BackupPaths:
    return BackupPaths(tmp, "https://dev.azure.com/myorg", "20240101T000000Z")


def _make_inv() -> Inventory:
    return Inventory()


REPO = {
    "id": "repo-abc",
    "name": "MyRepo",
    "remoteUrl": "https://dev.azure.com/myorg/MyProject/_git/MyRepo",
    "project": {"id": "proj-123", "name": "MyProject"},
}

ACL = [{"token": "repoV2/proj-123/repo-abc", "acesDictionary": {}}]


class TestRepoPermissions(unittest.TestCase):
    @patch("azcli.git_clone")
    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_permissions_file_written(self, mock_az, mock_invoke, mock_clone):
        """A {repo}_permissions.json file should be written per repo."""
        mock_az.return_value = [REPO]
        mock_invoke.side_effect = [
            {"value": []},   # branches
            {"value": []},   # tags
            {"value": []},   # policies
            {"value": ACL},  # accesscontrollists (permissions)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_git(bp, inv, "https://dev.azure.com/myorg", "MyProject")

            perms_path = bp.git_dir("MyProject") / "MyRepo_permissions.json"
            self.assertTrue(perms_path.exists(), "permissions file was not written")
            data = json.loads(perms_path.read_text())
            self.assertIsInstance(data, list)
            self.assertIn("acesDictionary", data[0])
            # "token" is a sensitive key and will be redacted
            self.assertEqual(data[0].get("token"), "***REDACTED***")

    @patch("azcli.git_clone")
    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_permissions_token_uses_project_and_repo_id(self, mock_az, mock_invoke, mock_clone):
        """The ACL query must use a token composed of the project and repo IDs."""
        mock_az.return_value = [REPO]
        mock_invoke.side_effect = [
            {"value": []},
            {"value": []},
            {"value": []},
            {"value": []},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_git(bp, inv, "https://dev.azure.com/myorg", "MyProject")

            # Find the accesscontrollists call and check its token
            acl_call = next(
                (c for c in mock_invoke.call_args_list
                 if c.args[1] == "accesscontrollists"),
                None,
            )
            self.assertIsNotNone(acl_call, "accesscontrollists was not called")
            token = acl_call.kwargs.get("query_parameters", {}).get("token", "")
            self.assertEqual(token, "repoV2/proj-123/repo-abc")

    @patch("azcli.git_clone")
    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_permissions_failure_non_fatal(self, mock_az, mock_invoke, mock_clone):
        """A permissions fetch failure should not abort the git backup."""
        mock_az.return_value = [REPO]
        mock_invoke.side_effect = [
            {"value": []},
            {"value": []},
            {"value": []},
            RuntimeError("403 Forbidden"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            # Should not raise
            backup_git(bp, inv, "https://dev.azure.com/myorg", "MyProject")

    @patch("azcli.git_clone")
    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_permissions_skipped_when_no_project_id(self, mock_az, mock_invoke, mock_clone):
        """If the repo object has no project.id, the permissions call should be skipped."""
        repo_no_proj = {**REPO, "project": {}}
        mock_az.return_value = [repo_no_proj]
        mock_invoke.side_effect = [
            {"value": []},
            {"value": []},
            {"value": []},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_git(bp, inv, "https://dev.azure.com/myorg", "MyProject")

            # Only 3 invoke calls (branches, tags, policies) — no permissions call
            self.assertEqual(mock_invoke.call_count, 3)

    @patch("azcli.git_clone")
    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_permissions_in_inventory(self, mock_az, mock_invoke, mock_clone):
        """Successful permissions export should be recorded in the inventory."""
        mock_az.return_value = [REPO]
        mock_invoke.side_effect = [
            {"value": []},
            {"value": []},
            {"value": []},
            {"value": ACL},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_git(bp, inv, "https://dev.azure.com/myorg", "MyProject")

            perm_entries = [
                e for e in inv.entries
                if "permissions" in e.get("name", "")
            ]
            self.assertTrue(len(perm_entries) > 0)


if __name__ == "__main__":
    unittest.main()
