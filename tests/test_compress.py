"""Tests for compression module."""

import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from compress import compress_all, compress_directory, compress_projects, compress_repos


class TestCompressDirectory(unittest.TestCase):
    def test_creates_archive_and_removes_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "mydir"
            src.mkdir()
            (src / "file.txt").write_text("hello")
            archive = compress_directory(src, Path(tmp) / "mydir.tar.gz")
            self.assertTrue(archive.exists())
            self.assertFalse(src.exists())
            with tarfile.open(archive) as tar:
                names = tar.getnames()
                self.assertIn("mydir/file.txt", names)

    def test_adds_suffix_if_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "data"
            src.mkdir()
            (src / "a.json").write_text("{}")
            archive = compress_directory(src, Path(tmp) / "data")
            self.assertTrue(archive.name.endswith(".tar.gz"))


class TestCompressRepos(unittest.TestCase):
    def test_compresses_repo_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "projects"
            repo1 = projects / "proj" / "git" / "repo1"
            repo2 = projects / "proj" / "git" / "repo2"
            repo1.mkdir(parents=True)
            repo2.mkdir(parents=True)
            (repo1 / "HEAD").write_text("ref: refs/heads/main")
            (repo2 / "HEAD").write_text("ref: refs/heads/main")
            # Also write repos.json to verify it's not compressed
            (projects / "proj" / "git" / "repos.json").write_text("[]")

            count = compress_repos(projects)
            self.assertEqual(count, 2)
            self.assertTrue((projects / "proj" / "git" / "repo1.tar.gz").exists())
            self.assertTrue((projects / "proj" / "git" / "repo2.tar.gz").exists())
            self.assertFalse(repo1.exists())
            self.assertFalse(repo2.exists())
            # repos.json should be untouched
            self.assertTrue((projects / "proj" / "git" / "repos.json").exists())

    def test_no_projects_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            count = compress_repos(Path(tmp) / "nonexistent")
            self.assertEqual(count, 0)


class TestCompressProjects(unittest.TestCase):
    def test_compresses_project_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            projects = Path(tmp) / "projects"
            (projects / "alpha" / "git").mkdir(parents=True)
            (projects / "alpha" / "git" / "repos.json").write_text("[]")
            (projects / "beta" / "boards").mkdir(parents=True)
            (projects / "beta" / "boards" / "tags.json").write_text("[]")

            count = compress_projects(projects)
            self.assertEqual(count, 2)
            self.assertTrue((projects / "alpha.tar.gz").exists())
            self.assertTrue((projects / "beta.tar.gz").exists())


class TestCompressAll(unittest.TestCase):
    def test_compresses_entire_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "20260101T000000Z"
            (base / "org").mkdir(parents=True)
            (base / "org" / "users.json").write_text("[]")
            (base / "_indexes").mkdir(parents=True)
            (base / "_indexes" / "manifest.json").write_text("{}")

            archive = compress_all(base)
            self.assertTrue(archive.exists())
            self.assertFalse(base.exists())
            with tarfile.open(archive) as tar:
                names = tar.getnames()
                self.assertTrue(any("users.json" in n for n in names))


if __name__ == "__main__":
    unittest.main()
