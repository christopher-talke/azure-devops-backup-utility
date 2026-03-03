"""Tests for configuration."""

import os
import unittest
from pathlib import Path
from types import SimpleNamespace

from config import ALL_COMPONENTS, BackupConfig, build_config


class TestBackupConfig(unittest.TestCase):
    def test_defaults(self):
        cfg = BackupConfig()
        self.assertEqual(cfg.org_url, "")
        self.assertEqual(cfg.concurrency, 4)
        self.assertFalse(cfg.fail_fast)
        self.assertFalse(cfg.dry_run)
        self.assertEqual(cfg.active_components, set(ALL_COMPONENTS))

    def test_active_components_excludes(self):
        cfg = BackupConfig(exclude={"git", "boards"})
        active = cfg.active_components
        self.assertNotIn("git", active)
        self.assertNotIn("boards", active)
        self.assertIn("org", active)

    def test_validate_missing_org_url(self):
        cfg = BackupConfig(pat="test")
        errors = cfg.validate()
        self.assertTrue(any("Organization URL" in e for e in errors))

    def test_validate_missing_pat(self):
        cfg = BackupConfig(org_url="https://dev.azure.com/test")
        errors = cfg.validate()
        self.assertTrue(any("PAT" in e for e in errors))

    def test_validate_ok(self):
        cfg = BackupConfig(org_url="https://dev.azure.com/test", pat="token")
        self.assertEqual(cfg.validate(), [])


class TestBuildConfig(unittest.TestCase):
    def test_env_vars(self):
        env = {
            "AZURE_DEVOPS_ORG_URL": "https://dev.azure.com/envorg",
            "AZURE_DEVOPS_EXT_PAT": "envpat",
        }
        original = {}
        for k, v in env.items():
            original[k] = os.environ.get(k)
            os.environ[k] = v
        try:
            cfg = build_config()
            self.assertEqual(cfg.org_url, "https://dev.azure.com/envorg")
            self.assertEqual(cfg.pat, "envpat")
        finally:
            for k, v in original.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_cli_args_override(self):
        env = {
            "AZURE_DEVOPS_ORG_URL": "https://dev.azure.com/envorg",
            "AZURE_DEVOPS_EXT_PAT": "envpat",
        }
        original = {}
        for k, v in env.items():
            original[k] = os.environ.get(k)
            os.environ[k] = v
        try:
            args = SimpleNamespace(
                org_url="https://dev.azure.com/cliorg",
                projects="proj1,proj2",
                include=None,
                exclude=None,
                since=None,
                max_items=100,
                concurrency=2,
                output_dir="custom-output",
                fail_fast=True,
                dry_run=False,
                verbose=True,
            )
            cfg = build_config(args)
            self.assertEqual(cfg.org_url, "https://dev.azure.com/cliorg")
            self.assertEqual(cfg.projects, ["proj1", "proj2"])
            self.assertEqual(cfg.max_items, 100)
            self.assertTrue(cfg.fail_fast)
        finally:
            for k, v in original.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


if __name__ == "__main__":
    unittest.main()
