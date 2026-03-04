"""Configuration: env vars, CLI flags, YAML config merge."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Attempt YAML import – stdlib only, so we use a simple parser fallback.
try:
    import yaml as _yaml  # type: ignore[import-untyped]
except ImportError:
    _yaml = None


def _parse_simple_yaml(path: Path) -> dict[str, Any]:
    """Minimal key: value parser for flat YAML files (no nesting)."""
    data: dict[str, Any] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip().strip("'\"")
        # Convert some common types
        if value.lower() in ("true", "yes"):
            data[key.strip()] = True
        elif value.lower() in ("false", "no"):
            data[key.strip()] = False
        elif value.isdigit():
            data[key.strip()] = int(value)
        else:
            data[key.strip()] = value
    return data


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file, falling back to a simple parser if PyYAML is absent."""
    if _yaml is not None:
        with open(path, encoding="utf-8") as fh:
            return _yaml.safe_load(fh) or {}
    return _parse_simple_yaml(path)


# All component names that can be included/excluded.
ALL_COMPONENTS = frozenset(
    {"org", "projects", "git", "boards", "pipelines", "permissions"}
)


@dataclass
class BackupConfig:
    """Merged configuration from env, CLI, and YAML."""

    org_url: str = ""
    pat: str = ""
    projects: list[str] = field(default_factory=list)  # empty means all
    include: set[str] = field(default_factory=lambda: set(ALL_COMPONENTS))
    exclude: set[str] = field(default_factory=set)
    since: str = ""
    max_items: int = 0  # 0 = unlimited
    concurrency: int = 4
    output_dir: str = "ado-backup"
    fail_fast: bool = False
    dry_run: bool = False
    verbose: bool = False
    timeout: int = 120

    @property
    def active_components(self) -> set[str]:
        return self.include - self.exclude

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.org_url:
            errors.append("Organization URL is required (--org-url or AZURE_DEVOPS_ORG_URL)")
        if not self.pat:
            logger.info("No PAT provided – relying on az CLI authentication (e.g. System.AccessToken in pipelines)")
        return errors


def build_config(args: Any | None = None, yaml_path: Path | None = None) -> BackupConfig:
    """Build a BackupConfig by merging YAML, env vars, and CLI args.

    Priority (highest wins): CLI args > env vars > YAML file > defaults.
    """
    cfg = BackupConfig()

    # 1. YAML file
    if yaml_path and yaml_path.exists():
        ydata = load_yaml(yaml_path)
        for key, value in ydata.items():
            key_under = key.replace("-", "_")
            if hasattr(cfg, key_under):
                current = getattr(cfg, key_under)
                if isinstance(current, set) and isinstance(value, list):
                    setattr(cfg, key_under, set(value))
                elif isinstance(current, list) and isinstance(value, str):
                    setattr(cfg, key_under, [v.strip() for v in value.split(",") if v.strip()])
                else:
                    setattr(cfg, key_under, value)

    # 2. Environment variables
    if os.environ.get("AZURE_DEVOPS_ORG_URL"):
        cfg.org_url = os.environ["AZURE_DEVOPS_ORG_URL"]
    # PAT: check AZURE_DEVOPS_EXT_PAT first, then fall back to SYSTEM_ACCESSTOKEN
    if os.environ.get("AZURE_DEVOPS_EXT_PAT"):
        cfg.pat = os.environ["AZURE_DEVOPS_EXT_PAT"]
    elif os.environ.get("SYSTEM_ACCESSTOKEN"):
        cfg.pat = os.environ["SYSTEM_ACCESSTOKEN"]
    if os.environ.get("ADO_BACKUP_OUTPUT_DIR"):
        cfg.output_dir = os.environ["ADO_BACKUP_OUTPUT_DIR"]
    if os.environ.get("ADO_BACKUP_TIMEOUT"):
        cfg.timeout = int(os.environ["ADO_BACKUP_TIMEOUT"])

    # 3. CLI args (argparse namespace)
    if args is not None:
        if getattr(args, "org_url", None):
            cfg.org_url = args.org_url
        if getattr(args, "projects", None):
            raw = args.projects
            if raw == "all":
                cfg.projects = []
            else:
                cfg.projects = [p.strip() for p in raw.split(",") if p.strip()]
        if getattr(args, "include", None):
            cfg.include = {c.strip() for c in args.include.split(",") if c.strip()}
        if getattr(args, "exclude", None):
            cfg.exclude = {c.strip() for c in args.exclude.split(",") if c.strip()}
        if getattr(args, "since", None):
            cfg.since = args.since
        if getattr(args, "max_items", None) is not None:
            cfg.max_items = args.max_items
        if getattr(args, "concurrency", None) is not None:
            cfg.concurrency = args.concurrency
        if getattr(args, "output_dir", None):
            cfg.output_dir = args.output_dir
        if getattr(args, "fail_fast", False):
            cfg.fail_fast = True
        if getattr(args, "dry_run", False):
            cfg.dry_run = True
        if getattr(args, "verbose", False):
            cfg.verbose = True

    cfg.org_url = cfg.org_url.rstrip("/")
    return cfg
