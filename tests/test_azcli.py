"""Tests for azcli wrapper error handling."""

import subprocess
import unittest
from unittest.mock import MagicMock, patch

from azcli import AzCliError, AzCliThrottled, _mask_pat, _run_az


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


if __name__ == "__main__":
    unittest.main()
