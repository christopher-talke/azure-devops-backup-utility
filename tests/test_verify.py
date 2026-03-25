"""Tests for verify.py."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure src/ is on path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from verify import (
    VerificationResult,
    VerificationReport,
    verify_backup,
    _verify_work_items,
    _verify_pipelines,
    _verify_wikis,
    _verify_git,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_backup_dir(tmp: Path) -> tuple[Path, Path]:
    """Create a minimal backup directory structure. Returns (backup_base, projects_dir)."""
    backup_base = tmp / "dev.azure.com" / "myorg" / "20240101T000000Z"
    indexes = backup_base / "_indexes"
    indexes.mkdir(parents=True)

    manifest = {
        "tool": "ado-backup",
        "version": "0.1.0",
        "started_at": "2024-01-01T00:00:00+00:00",
        "completed_at": "2024-01-01T01:00:00+00:00",
        "duration_seconds": 3600,
        "total_entities": 10,
        "total_errors": 0,
        "limits_applied": {"components": ["git", "boards", "pipelines", "pull_requests", "wikis", "artifacts"]},
    }
    (indexes / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    projects_dir = backup_base / "projects"
    projects_dir.mkdir(parents=True)
    return backup_base, projects_dir


def _make_project_dir(projects_dir: Path, name: str = "MyProject") -> Path:
    proj = projects_dir / name
    proj.mkdir(parents=True)
    return proj


# ---------------------------------------------------------------------------
# Work item tests
# ---------------------------------------------------------------------------

class TestVerifyWorkItems(unittest.TestCase):

    def _setup_work_item(self, proj_dir: Path, wi_id: int, rev: int, changed_date: str = "2023-12-01T00:00:00Z") -> Path:
        wi_dir = proj_dir / "boards" / "work_items"
        wi_dir.mkdir(parents=True, exist_ok=True)
        index = {"count": 1, "ids": [wi_id]}
        (wi_dir / "index.json").write_text(json.dumps(index), encoding="utf-8")
        item = {"id": wi_id, "fields": {"System.Rev": rev, "System.ChangedDate": changed_date}}
        (wi_dir / f"{wi_id}.json").write_text(json.dumps(item), encoding="utf-8")
        return wi_dir

    @patch("azcli.invoke")
    def test_verify_work_item_pass(self, mock_invoke):
        """Work item with matching System.Rev → pass."""
        with tempfile.TemporaryDirectory() as tmp:
            proj_dir = Path(tmp) / "proj"
            self._setup_work_item(proj_dir, wi_id=42, rev=5)
            mock_invoke.return_value = {"id": 42, "fields": {"System.Rev": 5}}

            results = _verify_work_items(proj_dir, "https://dev.azure.com/myorg", "MyProject",
                                         pat="", n=10, backup_started_at="2024-01-01T00:00:00+00:00")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "pass")
        self.assertEqual(results[0].backed_up_value, 5)
        self.assertEqual(results[0].live_value, 5)

    @patch("azcli.invoke")
    def test_verify_work_item_fail(self, mock_invoke):
        """Work item with higher live System.Rev → fail."""
        with tempfile.TemporaryDirectory() as tmp:
            proj_dir = Path(tmp) / "proj"
            self._setup_work_item(proj_dir, wi_id=42, rev=5)
            mock_invoke.return_value = {"id": 42, "fields": {"System.Rev": 7}}

            results = _verify_work_items(proj_dir, "https://dev.azure.com/myorg", "MyProject",
                                         pat="", n=10, backup_started_at="2024-01-01T00:00:00+00:00")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "fail")
        self.assertEqual(results[0].backed_up_value, 5)
        self.assertEqual(results[0].live_value, 7)

    @patch("azcli.invoke")
    def test_verify_work_item_skip_fresh(self, mock_invoke):
        """Work item modified after backup started → skip."""
        with tempfile.TemporaryDirectory() as tmp:
            proj_dir = Path(tmp) / "proj"
            # Changed date is after backup started
            self._setup_work_item(proj_dir, wi_id=42, rev=5,
                                  changed_date="2024-06-01T00:00:00Z")

            results = _verify_work_items(proj_dir, "https://dev.azure.com/myorg", "MyProject",
                                         pat="", n=10, backup_started_at="2024-01-01T00:00:00+00:00")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "skip")
        mock_invoke.assert_not_called()

    @patch("azcli.invoke")
    def test_verify_work_item_error(self, mock_invoke):
        """API call failure → error status."""
        with tempfile.TemporaryDirectory() as tmp:
            proj_dir = Path(tmp) / "proj"
            self._setup_work_item(proj_dir, wi_id=42, rev=5)
            mock_invoke.side_effect = RuntimeError("API unavailable")

            results = _verify_work_items(proj_dir, "https://dev.azure.com/myorg", "MyProject",
                                         pat="", n=10, backup_started_at="2024-01-01T00:00:00+00:00")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "error")
        self.assertIn("API unavailable", results[0].note)

    def test_verify_no_items_to_sample(self):
        """Empty index.json produces no results and does not crash."""
        with tempfile.TemporaryDirectory() as tmp:
            proj_dir = Path(tmp) / "proj"
            wi_dir = proj_dir / "boards" / "work_items"
            wi_dir.mkdir(parents=True)
            (wi_dir / "index.json").write_text(json.dumps({"count": 0, "ids": []}), encoding="utf-8")

            results = _verify_work_items(proj_dir, "https://dev.azure.com/myorg", "MyProject",
                                         pat="", n=5, backup_started_at="")

        self.assertEqual(results, [])


# ---------------------------------------------------------------------------
# Pipeline tests
# ---------------------------------------------------------------------------

class TestVerifyPipelines(unittest.TestCase):

    @patch("azcli.invoke")
    def test_verify_pipeline_pass(self, mock_invoke):
        """Pipeline with matching revision → pass."""
        with tempfile.TemporaryDirectory() as tmp:
            proj_dir = Path(tmp) / "proj"
            pipe_dir = proj_dir / "pipelines"
            pipe_dir.mkdir(parents=True)
            pipelines = [{"id": 10, "name": "CI", "revision": 3}]
            (pipe_dir / "pipelines.json").write_text(json.dumps(pipelines), encoding="utf-8")
            mock_invoke.return_value = {"id": 10, "name": "CI", "revision": 3}

            results = _verify_pipelines(proj_dir, "https://dev.azure.com/myorg", "MyProject",
                                        pat="", n=10, backup_started_at="")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "pass")

    @patch("azcli.invoke")
    def test_verify_pipeline_fail(self, mock_invoke):
        """Pipeline with different live revision → fail."""
        with tempfile.TemporaryDirectory() as tmp:
            proj_dir = Path(tmp) / "proj"
            pipe_dir = proj_dir / "pipelines"
            pipe_dir.mkdir(parents=True)
            pipelines = [{"id": 10, "name": "CI", "revision": 3}]
            (pipe_dir / "pipelines.json").write_text(json.dumps(pipelines), encoding="utf-8")
            mock_invoke.return_value = {"id": 10, "name": "CI", "revision": 5}

            results = _verify_pipelines(proj_dir, "https://dev.azure.com/myorg", "MyProject",
                                        pat="", n=10, backup_started_at="")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "fail")
        self.assertEqual(results[0].backed_up_value, 3)
        self.assertEqual(results[0].live_value, 5)


# ---------------------------------------------------------------------------
# Wiki tests
# ---------------------------------------------------------------------------

class TestVerifyWikis(unittest.TestCase):

    def test_verify_wiki_pass(self):
        """Wiki with non-empty pages file → pass."""
        with tempfile.TemporaryDirectory() as tmp:
            proj_dir = Path(tmp) / "proj"
            wikis_dir = proj_dir / "wikis"
            wikis_dir.mkdir(parents=True)
            wikis = [{"id": "w1", "name": "ProjectWiki"}]
            (wikis_dir / "wikis.json").write_text(json.dumps(wikis), encoding="utf-8")
            (wikis_dir / "wiki_ProjectWiki_pages.json").write_text(
                json.dumps({"id": "w1", "subPages": []}), encoding="utf-8"
            )

            results = _verify_wikis(proj_dir, "https://dev.azure.com/myorg", "MyProject",
                                    pat="", n=10, backup_started_at="")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "pass")

    def test_verify_wiki_missing_pages_file(self):
        """Wiki with missing pages file → skip."""
        with tempfile.TemporaryDirectory() as tmp:
            proj_dir = Path(tmp) / "proj"
            wikis_dir = proj_dir / "wikis"
            wikis_dir.mkdir(parents=True)
            wikis = [{"id": "w1", "name": "ProjectWiki"}]
            (wikis_dir / "wikis.json").write_text(json.dumps(wikis), encoding="utf-8")

            results = _verify_wikis(proj_dir, "https://dev.azure.com/myorg", "MyProject",
                                    pat="", n=10, backup_started_at="")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "skip")


# ---------------------------------------------------------------------------
# Git tests (subprocess mocked)
# ---------------------------------------------------------------------------

class TestVerifyGit(unittest.TestCase):

    @patch("azcli.invoke")
    @patch("subprocess.run")
    def test_verify_git_pass(self, mock_run, mock_invoke):
        """Bare clone HEAD SHA matches live API → pass."""
        with tempfile.TemporaryDirectory() as tmp:
            proj_dir = Path(tmp) / "proj"
            git_dir = proj_dir / "git"
            git_dir.mkdir(parents=True)

            repos = [{
                "id": "repo-uuid-1",
                "name": "MyRepo",
                "defaultBranch": "refs/heads/main",
            }]
            (git_dir / "repos.json").write_text(json.dumps(repos), encoding="utf-8")

            # Simulate the bare repo HEAD file existing
            bare = git_dir / "MyRepo"
            bare.mkdir()
            (bare / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")

            sha = "abc123def456abc123def456abc123def456abc1"
            mock_run.return_value = MagicMock(returncode=0, stdout=sha + "\n")
            mock_invoke.return_value = {"value": [{"objectId": sha}]}

            results = _verify_git(proj_dir, "https://dev.azure.com/myorg", "MyProject",
                                  pat="", n=10, backup_started_at="")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "pass")
        self.assertEqual(results[0].backed_up_value, sha)
        self.assertEqual(results[0].live_value, sha)

    @patch("azcli.invoke")
    @patch("subprocess.run")
    def test_verify_git_fail(self, mock_run, mock_invoke):
        """Different SHA between backup and live → fail."""
        with tempfile.TemporaryDirectory() as tmp:
            proj_dir = Path(tmp) / "proj"
            git_dir = proj_dir / "git"
            git_dir.mkdir(parents=True)

            repos = [{"id": "repo-uuid-1", "name": "MyRepo", "defaultBranch": "refs/heads/main"}]
            (git_dir / "repos.json").write_text(json.dumps(repos), encoding="utf-8")

            bare = git_dir / "MyRepo"
            bare.mkdir()
            (bare / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")

            local_sha = "aaaaabbbbbcccccaaaaabbbbbcccccaaaaabbbbb"
            live_sha  = "111112222233333111112222233333111112222"
            mock_run.return_value = MagicMock(returncode=0, stdout=local_sha + "\n")
            mock_invoke.return_value = {"value": [{"objectId": live_sha}]}

            results = _verify_git(proj_dir, "https://dev.azure.com/myorg", "MyProject",
                                  pat="", n=10, backup_started_at="")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "fail")


# ---------------------------------------------------------------------------
# Full report structure tests
# ---------------------------------------------------------------------------

class TestVerifyReportStructure(unittest.TestCase):

    @patch("azcli.invoke")
    def test_verify_report_structure(self, mock_invoke):
        """verify_backup() writes a valid verification_report.json with correct keys."""
        mock_invoke.return_value = {"id": 1, "fields": {"System.Rev": 2}}

        with tempfile.TemporaryDirectory() as tmp:
            backup_base, projects_dir = _make_backup_dir(Path(tmp))
            proj_dir = _make_project_dir(projects_dir)

            # Add a work item
            wi_dir = proj_dir / "boards" / "work_items"
            wi_dir.mkdir(parents=True)
            (wi_dir / "index.json").write_text(json.dumps({"count": 1, "ids": [1]}), encoding="utf-8")
            (wi_dir / "1.json").write_text(
                json.dumps({"id": 1, "fields": {"System.Rev": 2, "System.ChangedDate": "2023-06-01T00:00:00Z"}}),
                encoding="utf-8",
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="")
                report = verify_backup(backup_base, "https://dev.azure.com/myorg", samples=1)

            # Report file written (assertions inside with block — tmpdir still alive)
            report_file = backup_base / "_indexes" / "verification_report.json"
            self.assertTrue(report_file.exists())

            data = json.loads(report_file.read_text(encoding="utf-8"))
            for key in ("verified_at", "backup_path", "org_url", "samples_per_category", "summary", "results"):
                self.assertIn(key, data)

            summary = data["summary"]
            for key in ("total", "passed", "failed", "skipped", "errors"):
                self.assertIn(key, summary)
            self.assertEqual(summary["total"], len(data["results"]))

    def test_report_summary_counts(self):
        """VerificationReport.summary correctly counts each status."""
        report = VerificationReport(
            verified_at="2024-01-01T00:00:00+00:00",
            backup_path="/tmp/backup",
            org_url="https://dev.azure.com/myorg",
            samples_per_category=3,
            results=[
                VerificationResult("boards", "P", "wi/1", "pass", "rev", 1, 1),
                VerificationResult("boards", "P", "wi/2", "fail", "rev", 1, 2),
                VerificationResult("git",    "P", "repo/A", "skip", "sha"),
                VerificationResult("git",    "P", "repo/B", "error", "sha"),
            ],
        )
        s = report.summary
        self.assertEqual(s["total"], 4)
        self.assertEqual(s["passed"], 1)
        self.assertEqual(s["failed"], 1)
        self.assertEqual(s["skipped"], 1)
        self.assertEqual(s["errors"], 1)


if __name__ == "__main__":
    unittest.main()
