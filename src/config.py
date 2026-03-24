"""Configuration: env vars, CLI flags, YAML config merge."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field, fields as dataclass_fields
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
    compress: str = ""  # "", "repos", "project", "all"
    output_dir: str = "ado-backup"
    fail_fast: bool = False
    dry_run: bool = False
    verbose: bool = False
    timeout: int = 120

    # Allowed compress values
    _VALID_COMPRESS = ("", "repos", "project", "all")

    @property
    def active_components(self) -> set[str]:
        return self.include - self.exclude

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.org_url:
            errors.append("Organization URL is required (--org-url or AZURE_DEVOPS_ORG_URL)")
        if not self.pat:
            logger.info("No PAT provided – relying on az CLI authentication (e.g. System.AccessToken in pipelines)")
        if self.compress and self.compress not in self._VALID_COMPRESS:
            errors.append(f"Invalid --compress value '{self.compress}'; must be one of: repos, project, all")
        invalid_inc = self.include - ALL_COMPONENTS
        if invalid_inc:
            errors.append(f"Unknown --include components: {', '.join(sorted(invalid_inc))}")
        invalid_exc = self.exclude - ALL_COMPONENTS
        if invalid_exc:
            errors.append(f"Unknown --exclude components: {', '.join(sorted(invalid_exc))}")
        # Reject path traversal in output_dir
        resolved = Path(self.output_dir).resolve()
        if ".." in Path(self.output_dir).parts:
            errors.append(f"output_dir must not contain '..': {self.output_dir}")
        return errors


def build_config(args: Any | None = None, yaml_path: Path | None = None) -> BackupConfig:
    """Build a BackupConfig by merging YAML, env vars, and CLI args.

    Priority (highest wins): CLI args > env vars > YAML file > defaults.
    """
    cfg = BackupConfig()

    # 1. YAML file
    _allowed_fields = {f.name for f in dataclass_fields(BackupConfig)}
    if yaml_path and yaml_path.exists():
        ydata = load_yaml(yaml_path)
        for key, value in ydata.items():
            key_under = key.replace("-", "_")
            if key_under not in _allowed_fields:
                logger.warning("Ignoring unknown YAML key: %s", key)
                continue
            current = getattr(cfg, key_under)
            if isinstance(current, set) and isinstance(value, list):
                setattr(cfg, key_under, set(value))
            elif isinstance(current, list) and isinstance(value, str):
                setattr(cfg, key_under, [v.strip() for v in value.split(",") if v.strip()])
            else:
                setattr(cfg, key_under, value)

    if cfg.pat:
        logger.warning(
            "PAT found in YAML config file. Storing credentials in config files is "
            "discouraged. Use the AZURE_DEVOPS_EXT_PAT environment variable instead."
        )

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
        _raw_timeout = os.environ["ADO_BACKUP_TIMEOUT"]
        try:
            cfg.timeout = int(_raw_timeout)
        except ValueError:
            logger.warning(
                "ADO_BACKUP_TIMEOUT=%r is not a valid integer; using default (%ds)",
                _raw_timeout,
                cfg.timeout,
            )

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
        if getattr(args, "compress", None):
            cfg.compress = args.compress
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
