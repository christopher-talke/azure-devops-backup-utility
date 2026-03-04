"""Orchestrates the full backup flow."""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import Any

import azcli
from config import BackupConfig
from inventory import Inventory
from paths import BackupPaths
from scopes import boards, git, org, permissions, pipelines, projects

logger = logging.getLogger(__name__)


def run_backup(cfg: BackupConfig) -> int:
    """Execute the full backup and return an exit code (0 = success)."""
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = Path(cfg.output_dir)
    bp = BackupPaths(root, cfg.org_url, timestamp)
    inv = Inventory()
    inv.set_limits(
        {
            "max_items": cfg.max_items,
            "since": cfg.since,
            "components": sorted(cfg.active_components),
        }
    )

    logger.info("Backup started at %s", timestamp)
    logger.info("Organisation: %s", cfg.org_url)
    logger.info("Output root : %s", bp.base)
    logger.info("Components  : %s", ", ".join(sorted(cfg.active_components)))

    if cfg.dry_run:
        logger.info("DRY-RUN mode – no data will be written")

    # Ensure Azure DevOps extension
    if not cfg.dry_run:
        try:
            azcli.ensure_devops_extension()
        except Exception as exc:
            logger.error("Cannot proceed without Azure CLI: %s", exc)
            return 1

        azcli.configure_defaults(cfg.org_url)

    active = cfg.active_components

    # Organisation-level backup
    if "org" in active:
        try:
            org.backup_org(bp, inv, cfg.org_url, dry_run=cfg.dry_run)
        except Exception as exc:
            logger.error("Organisation backup failed: %s", exc)
            inv.add_error("org", "org", str(exc))
            if cfg.fail_fast:
                _write_indexes(bp, inv)
                return 1

    # Enumerate projects
    project_list: list[dict[str, Any]] = []
    if any(c in active for c in ("projects", "git", "boards", "pipelines", "permissions")):
        try:
            if cfg.dry_run:
                logger.info("[DRY-RUN] Would list projects")
                project_list = [{"name": p} for p in cfg.projects] if cfg.projects else []
            else:
                project_list = projects.list_projects(cfg.org_url)
                if cfg.projects:
                    allowed = {p.lower() for p in cfg.projects}
                    project_list = [p for p in project_list if p.get("name", "").lower() in allowed]
                logger.info("Found %d project(s) to back up", len(project_list))
        except Exception as exc:
            logger.error("Failed to list projects: %s", exc)
            inv.add_error("projects", "list", str(exc))
            if cfg.fail_fast:
                _write_indexes(bp, inv)
                return 1

    # Process each project
    for proj in project_list:
        pname = proj.get("name", "unknown")
        logger.info("Processing project '%s' …", pname)

        if not cfg.dry_run:
            try:
                azcli.configure_defaults(cfg.org_url, pname)
            except Exception:
                pass

        if "projects" in active:
            _safe_call(
                projects.backup_project_metadata,
                bp, inv, cfg.org_url, pname,
                dry_run=cfg.dry_run,
                fail_fast=cfg.fail_fast,
                inv=inv, category="projects", name=pname,
            )

        if "git" in active:
            _safe_call(
                git.backup_git,
                bp, inv, cfg.org_url, pname, cfg.pat,
                dry_run=cfg.dry_run, max_items=cfg.max_items,
                fail_fast=cfg.fail_fast,
                inv=inv, category="git", name=pname,
            )

        if "boards" in active:
            _safe_call(
                boards.backup_boards,
                bp, inv, cfg.org_url, pname,
                dry_run=cfg.dry_run, max_items=cfg.max_items,
                fail_fast=cfg.fail_fast,
                inv=inv, category="boards", name=pname,
            )

        if "pipelines" in active:
            _safe_call(
                pipelines.backup_pipelines,
                bp, inv, cfg.org_url, pname,
                dry_run=cfg.dry_run, max_items=cfg.max_items,
                fail_fast=cfg.fail_fast,
                inv=inv, category="pipelines", name=pname,
            )

        if "permissions" in active:
            _safe_call(
                permissions.backup_permissions,
                bp, inv, cfg.org_url, pname,
                dry_run=cfg.dry_run,
                fail_fast=cfg.fail_fast,
                inv=inv, category="permissions", name=pname,
            )

    _write_indexes(bp, inv)

    # Summary
    logger.info("=" * 60)
    logger.info("Backup complete: %d entities, %d errors", len(inv.entries), len(inv.errors))
    if inv.errors:
        logger.warning("Errors occurred – see %s", bp.errors_file())
    logger.info("Output: %s", bp.base)

    return 1 if inv.errors and cfg.fail_fast else 0


def _safe_call(func: Any, *args: Any, fail_fast: bool = False, inv: Inventory | None = None,
               category: str = "", name: str = "", **kwargs: Any) -> None:
    """Call *func* and catch exceptions unless fail_fast is set."""
    try:
        func(*args, **kwargs)
    except Exception as exc:
        logger.error("%s backup failed for '%s': %s", category, name, exc)
        if inv:
            inv.add_error(category, name, str(exc))
        if fail_fast:
            raise


def _write_indexes(bp: BackupPaths, inv: Inventory) -> None:
    """Write manifest, inventory, and errors files."""
    try:
        inv.write(bp.inventory_file(), bp.manifest_file(), bp.errors_file())
    except Exception as exc:
        logger.error("Failed to write indexes: %s", exc)
