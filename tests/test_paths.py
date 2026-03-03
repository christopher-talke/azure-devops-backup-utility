"""Tests for path utilities."""

import unittest
from pathlib import Path

from ado_backup.paths import BackupPaths, parse_org_url, safe_name


class TestSafeName(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(safe_name("my-project"), "my-project")

    def test_spaces_replaced(self):
        self.assertEqual(safe_name("my project"), "my_project")

    def test_special_chars(self):
        self.assertEqual(safe_name("a/b\\c:d"), "a_b_c_d")


class TestParseOrgUrl(unittest.TestCase):
    def test_modern_url(self):
        host, org = parse_org_url("https://dev.azure.com/myorg")
        self.assertEqual(host, "dev.azure.com")
        self.assertEqual(org, "myorg")

    def test_modern_url_trailing_slash(self):
        host, org = parse_org_url("https://dev.azure.com/myorg/")
        self.assertEqual(host, "dev.azure.com")
        self.assertEqual(org, "myorg")

    def test_legacy_url(self):
        host, org = parse_org_url("https://myorg.visualstudio.com")
        self.assertEqual(host, "myorg.visualstudio.com")
        self.assertEqual(org, "myorg")


class TestBackupPaths(unittest.TestCase):
    def setUp(self):
        self.bp = BackupPaths(Path("/tmp/backup"), "https://dev.azure.com/testorg", "20240101T000000Z")

    def test_base_path(self):
        self.assertEqual(
            self.bp.base,
            Path("/tmp/backup/dev.azure.com/testorg/20240101T000000Z"),
        )

    def test_org_file(self):
        self.assertEqual(
            self.bp.org_file("users.json"),
            Path("/tmp/backup/dev.azure.com/testorg/20240101T000000Z/org/users.json"),
        )

    def test_project_dir(self):
        self.assertEqual(
            self.bp.project_dir("MyProject"),
            Path("/tmp/backup/dev.azure.com/testorg/20240101T000000Z/projects/MyProject"),
        )

    def test_git_dir(self):
        self.assertEqual(
            self.bp.git_dir("MyProject"),
            Path("/tmp/backup/dev.azure.com/testorg/20240101T000000Z/projects/MyProject/git"),
        )

    def test_repo_dir(self):
        self.assertEqual(
            self.bp.repo_dir("MyProject", "my-repo"),
            Path("/tmp/backup/dev.azure.com/testorg/20240101T000000Z/projects/MyProject/git/my-repo"),
        )

    def test_boards_dir(self):
        self.assertEqual(
            self.bp.boards_dir("MyProject"),
            Path("/tmp/backup/dev.azure.com/testorg/20240101T000000Z/projects/MyProject/boards"),
        )

    def test_work_items_dir(self):
        self.assertEqual(
            self.bp.work_items_dir("MyProject"),
            Path("/tmp/backup/dev.azure.com/testorg/20240101T000000Z/projects/MyProject/boards/work_items"),
        )

    def test_pipelines_dir(self):
        self.assertEqual(
            self.bp.pipelines_dir("MyProject"),
            Path("/tmp/backup/dev.azure.com/testorg/20240101T000000Z/projects/MyProject/pipelines"),
        )

    def test_manifest_file(self):
        self.assertEqual(
            self.bp.manifest_file(),
            Path("/tmp/backup/dev.azure.com/testorg/20240101T000000Z/_indexes/manifest.json"),
        )


if __name__ == "__main__":
    unittest.main()
