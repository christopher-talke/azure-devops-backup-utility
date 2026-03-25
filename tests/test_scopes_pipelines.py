"""Tests for scopes/pipelines.py."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from inventory import Inventory
from paths import BackupPaths
from scopes.pipelines import backup_pipelines


def _make_paths(tmp: Path) -> BackupPaths:
    return BackupPaths(tmp, "https://dev.azure.com/myorg", "20240101T000000Z")


def _make_inv() -> Inventory:
    return Inventory()


BUILD = {"id": 101, "buildNumber": "20240101.1", "status": "completed"}
LOG_ENTRY = {"id": 1, "type": "Console", "url": "https://dev.azure.com/myorg/_apis/build/builds/101/logs/1"}


class TestBackupPipelines(unittest.TestCase):
    @patch("azcli.download_binary")
    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_log_download_triggered_per_build(self, mock_az, mock_invoke, mock_download):
        """Each build in the runs index should trigger a log download attempt."""
        mock_az.return_value = [{"id": 1, "name": "MyPipeline"}]  # az pipelines list
        mock_invoke.side_effect = [
            # runs_index (builds)
            {"value": [BUILD]},
            # logs for build 101
            {"value": [LOG_ENTRY]},
            # environments
            {"value": []},
            # secure files
            {"value": []},
            # task groups
            {"value": []},
            # release definitions
            {"value": []},
        ]

        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_pipelines(bp, inv, "https://dev.azure.com/myorg", "MyProject")
            mock_download.assert_called_once()
            call_url = mock_download.call_args[0][0]
            self.assertIn("101/logs/1", call_url)

    @patch("azcli.download_binary")
    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_log_stored_in_correct_path(self, mock_az, mock_invoke, mock_download):
        mock_az.return_value = [{"id": 1, "name": "MyPipeline"}]
        mock_invoke.side_effect = [
            {"value": [BUILD]},
            {"value": [LOG_ENTRY]},
            {"value": []},
            {"value": []},
            {"value": []},
            {"value": []},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_pipelines(bp, inv, "https://dev.azure.com/myorg", "MyProject")
            dest_path: Path = mock_download.call_args[0][1]
            self.assertEqual(dest_path.name, "1.txt")
            self.assertIn("101", str(dest_path))

    @patch("azcli.download_binary")
    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_log_failure_non_fatal(self, mock_az, mock_invoke, mock_download):
        """A log download failure should not abort the pipeline backup."""
        mock_az.return_value = []
        mock_invoke.side_effect = [
            {"value": [BUILD]},
            RuntimeError("log fetch failed"),
            {"value": []},
            {"value": []},
            {"value": []},
            {"value": []},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            # Should not raise
            backup_pipelines(bp, inv, "https://dev.azure.com/myorg", "MyProject")

    @patch("azcli.download_binary")
    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_dry_run_writes_nothing(self, mock_az, mock_invoke, mock_download):
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_pipelines(bp, inv, "https://dev.azure.com/myorg", "MyProject",
                              dry_run=True)
            mock_az.assert_not_called()
            mock_invoke.assert_not_called()
            mock_download.assert_not_called()

    @patch("azcli.download_binary")
    @patch("azcli.invoke")
    @patch("azcli.az")
    def test_runs_index_written(self, mock_az, mock_invoke, mock_download):
        mock_az.return_value = []
        mock_invoke.side_effect = [
            {"value": [BUILD]},
            {"value": []},   # logs (empty)
            {"value": []},
            {"value": []},
            {"value": []},
            {"value": []},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            bp = _make_paths(Path(tmp))
            inv = _make_inv()
            backup_pipelines(bp, inv, "https://dev.azure.com/myorg", "MyProject")
            pipe_dir = bp.pipelines_dir("MyProject")
            self.assertTrue((pipe_dir / "runs_index.json").exists())
            data = json.loads((pipe_dir / "runs_index.json").read_text())
            self.assertEqual(data[0]["id"], 101)


if __name__ == "__main__":
    unittest.main()
