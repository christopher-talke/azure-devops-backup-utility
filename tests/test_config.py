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

    def test_validate_no_pat_is_ok(self):
        cfg = BackupConfig(org_url="https://dev.azure.com/test")
        errors = cfg.validate()
        self.assertEqual(errors, [])

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

    def test_system_accesstoken_fallback(self):
        original_pat = os.environ.pop("AZURE_DEVOPS_EXT_PAT", None)
        original_sys = os.environ.pop("SYSTEM_ACCESSTOKEN", None)
        os.environ["SYSTEM_ACCESSTOKEN"] = "systoken"
        try:
            cfg = build_config()
            self.assertEqual(cfg.pat, "systoken")
        finally:
            os.environ.pop("SYSTEM_ACCESSTOKEN", None)
            if original_pat is not None:
                os.environ["AZURE_DEVOPS_EXT_PAT"] = original_pat
            if original_sys is not None:
                os.environ["SYSTEM_ACCESSTOKEN"] = original_sys

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


class TestBuildConfigTimeout(unittest.TestCase):
    def _set_env(self, key, value):
        """Helper to set an env var and return the original value."""
        original = os.environ.get(key)
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
        return original

    def _restore_env(self, key, original):
        if original is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original

    def test_valid_timeout(self):
        original = self._set_env("ADO_BACKUP_TIMEOUT", "300")
        try:
            cfg = build_config()
            self.assertEqual(cfg.timeout, 300)
        finally:
            self._restore_env("ADO_BACKUP_TIMEOUT", original)

    def test_invalid_timeout_uses_default(self):
        """A non-integer ADO_BACKUP_TIMEOUT should not raise; default (120) is kept."""
        original = self._set_env("ADO_BACKUP_TIMEOUT", "not-a-number")
        try:
            cfg = build_config()
            self.assertEqual(cfg.timeout, 120)
        finally:
            self._restore_env("ADO_BACKUP_TIMEOUT", original)


if __name__ == "__main__":
    unittest.main()
