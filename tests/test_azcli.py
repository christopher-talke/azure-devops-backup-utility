"""Tests for azcli wrapper error handling."""

import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from azcli import AzCliError, AzCliThrottled, _mask_pat, _run_az, git_clone


class TestMaskPat(unittest.TestCase):
    def test_no_pat(self):
        cmd = ["az", "devops", "project", "list"]
        self.assertEqual(_mask_pat(cmd), cmd)

    def test_mask_pat(self):
        cmd = ["az", "devops", "--pat", "secret123"]
        masked = _mask_pat(cmd)
        self.assertEqual(masked, ["az", "devops", "--pat", "***"])


class TestRunAz(unittest.TestCase):
    @patch("azcli.subprocess.run")
    def test_success_json(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"key": "value"}',
            stderr="",
        )
        result = _run_az(["az", "test"], parse_json=True)
        self.assertEqual(result, {"key": "value"})

    @patch("azcli.subprocess.run")
    def test_failure_raises(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Something went wrong",
        )
        with self.assertRaises(AzCliError):
            _run_az(["az", "test"])

    @patch("azcli.subprocess.run")
    def test_throttle_429(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="HTTP 429 TooManyRequests",
        )
        with self.assertRaises(AzCliThrottled):
            _run_az(["az", "test"])

    @patch("azcli.subprocess.run")
    def test_empty_output(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="",
        )
        result = _run_az(["az", "test"], parse_json=True)
        self.assertIsNone(result)

    @patch("azcli.subprocess.run")
    def test_raw_output(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="plain text output",
            stderr="",
        )
        result = _run_az(["az", "test"], parse_json=False)
        self.assertEqual(result, "plain text output")


class TestInvokePagination(unittest.TestCase):
    @patch("azcli.retry")
    @patch("azcli.logger")
    def test_logs_warning_when_max_pages_reached_with_token(self, mock_logger, mock_retry):
        mock_retry.side_effect = [
            {"value": [1], "continuationToken": "next-token"},
            {"value": [2], "continuationToken": "still-more"},
        ]
        from azcli import invoke
        result = invoke("build", "builds", max_pages=2)
        self.assertEqual(result["value"], [1, 2])
        mock_logger.warning.assert_called_once()


class TestGitClonePATScrubbing(unittest.TestCase):
    @patch("azcli.subprocess.run")
    def test_pat_scrubbed_from_error_message(self, mock_run):
        """PAT must not appear in AzCliError when git clone fails."""
        secret = "super_secret_token"
        mock_run.return_value = MagicMock(
            returncode=128,
            stdout="",
            stderr=f"fatal: repository 'https://x-token:{secret}@dev.azure.com/org/repo' not found",
        )
        with self.assertRaises(AzCliError) as ctx:
            git_clone("https://dev.azure.com/org/repo", Path("/tmp/dest"), pat=secret)
        self.assertNotIn(secret, str(ctx.exception))
        self.assertNotIn(secret, ctx.exception.stderr)

    @patch("azcli.subprocess.run")
    def test_no_pat_error_message_unchanged(self, mock_run):
        """When no PAT is provided, stderr is passed through as-is."""
        mock_run.return_value = MagicMock(
            returncode=128,
            stdout="",
            stderr="fatal: repository not found",
        )
        with self.assertRaises(AzCliError) as ctx:
            git_clone("https://dev.azure.com/org/repo", Path("/tmp/dest"))
        self.assertIn("fatal: repository not found", str(ctx.exception))

    @patch("azcli.subprocess.run")
    def test_successful_clone_no_error(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        # Should not raise
        git_clone("https://dev.azure.com/org/repo", Path("/tmp/dest"), pat="mytoken")


if __name__ == "__main__":
    unittest.main()
