"""CLI entry point for ado-backup."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from config import ALL_COMPONENTS, build_config

_COMPONENT_LIST = ",".join(sorted(ALL_COMPONENTS))


def _build_parser():
    """Build the argument parser."""
    import argparse

    parser = argparse.ArgumentParser(prog="ado-backup", description="Azure DevOps Backup Utility – back up organisations, projects, repos, boards, pipelines and more.")
    parser.add_argument("--org-url", help="Azure DevOps organisation URL (default: $AZURE_DEVOPS_ORG_URL)")
    parser.add_argument("--projects", default="all", help="Comma-separated project names or 'all' (default: all)")
    parser.add_argument("--include", help=f"Comma-separated components to include: {_COMPONENT_LIST}")
    parser.add_argument("--exclude", help=f"Comma-separated components to exclude: {_COMPONENT_LIST}")
    parser.add_argument("--since", help="ISO timestamp for incremental-like filtering")
    parser.add_argument("--max-items", type=int, default=0, help="Per-entity item limit (0 = unlimited)")
    parser.add_argument("--compress", choices=["repos", "project", "all"], help="Compress output: repos (each clone), project (per-project), all (entire backup)")
    parser.add_argument("--output-dir", default="ado-backup", help="Root output directory (default: ado-backup)")
    parser.add_argument("--config", help="Path to YAML configuration file")
    parser.add_argument("--fail-fast", action="store_true", help="Abort on first error")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without writing data")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--verify", action="store_true", help="After backup, verify a random sample of items against the live instance")
    parser.add_argument("--verify-samples", type=int, default=3, metavar="N", help="Items to sample per category during verification (default: 3)")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
        stream=sys.stderr,
    )

    yaml_path = Path(args.config) if args.config else None
    cfg = build_config(args, yaml_path)

    errors = cfg.validate()
    if errors:
        for e in errors:
            logging.error(e)
        return 2

    from orchestrator import run_backup

    return run_backup(cfg)


if __name__ == "__main__":
    sys.exit(main())
