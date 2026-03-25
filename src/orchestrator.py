"""Orchestrates the full backup flow."""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import Any

import azcli
import compress as _compress
from config import BackupConfig
from inventory import Inventory
from paths import BackupPaths
from scopes import (
    artifacts, boards, dashboards, git, org, permissions, pipelines,
    projects, pull_requests, testplans, wikis,
)

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
            org.backup_org(bp, inv, cfg.org_url, pat=cfg.pat, dry_run=cfg.dry_run)
        except Exception as exc:
            logger.error("Organisation backup failed: %s", exc)
            inv.add_error("org", "org", str(exc), pat=cfg.pat)
            if cfg.fail_fast:
                _write_indexes(bp, inv)
                return 1

    # Enumerate projects
    project_list: list[dict[str, Any]] = []
    if any(c in active for c in ("projects", "git", "boards", "pipelines", "permissions",
                                    "pull_requests", "artifacts", "dashboards", "wikis",
                                    "testplans")):
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
            inv.add_error("projects", "list", str(exc), pat=cfg.pat)
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
            except Exception as exc:
                logger.warning("configure_defaults failed for '%s': %s", pname, exc)

        if "projects" in active:
            _safe_call(
                projects.backup_project_metadata,
                bp, inv, cfg.org_url, pname,
                dry_run=cfg.dry_run,
                fail_fast=cfg.fail_fast,
                inv=inv, category="projects", name=pname, pat=cfg.pat,
            )

        if "git" in active:
            _safe_call(
                git.backup_git,
                bp, inv, cfg.org_url, pname,
                dry_run=cfg.dry_run, max_items=cfg.max_items,
                fail_fast=cfg.fail_fast,
                inv=inv, category="git", name=pname, pat=cfg.pat,
            )

        if "boards" in active:
            _safe_call(
                boards.backup_boards,
                bp, inv, cfg.org_url, pname,
                dry_run=cfg.dry_run, max_items=cfg.max_items, since=cfg.since,
                fail_fast=cfg.fail_fast,
                inv=inv, category="boards", name=pname, pat=cfg.pat,
            )

        if "pipelines" in active:
            _safe_call(
                pipelines.backup_pipelines,
                bp, inv, cfg.org_url, pname,
                dry_run=cfg.dry_run, max_items=cfg.max_items, since=cfg.since,
                fail_fast=cfg.fail_fast,
                inv=inv, category="pipelines", name=pname, pat=cfg.pat,
            )

        if "permissions" in active:
            _safe_call(
                permissions.backup_permissions,
                bp, inv, cfg.org_url, pname,
                dry_run=cfg.dry_run,
                fail_fast=cfg.fail_fast,
                inv=inv, category="permissions", name=pname, pat=cfg.pat,
            )

        if "pull_requests" in active:
            _safe_call(
                pull_requests.backup_pull_requests,
                bp, inv, cfg.org_url, pname,
                dry_run=cfg.dry_run, max_items=cfg.max_items, since=cfg.since,
                fail_fast=cfg.fail_fast,
                inv=inv, category="pull_requests", name=pname, pat=cfg.pat,
            )

        if "artifacts" in active:
            _safe_call(
                artifacts.backup_artifacts,
                bp, inv, cfg.org_url, pname,
                dry_run=cfg.dry_run, max_items=cfg.max_items,
                fail_fast=cfg.fail_fast,
                inv=inv, category="artifacts", name=pname, pat=cfg.pat,
            )

        if "dashboards" in active:
            _safe_call(
                dashboards.backup_dashboards,
                bp, inv, cfg.org_url, pname,
                dry_run=cfg.dry_run,
                fail_fast=cfg.fail_fast,
                inv=inv, category="dashboards", name=pname, pat=cfg.pat,
            )

        if "wikis" in active:
            _safe_call(
                wikis.backup_wikis,
                bp, inv, cfg.org_url, pname,
                dry_run=cfg.dry_run, max_items=cfg.max_items,
                fail_fast=cfg.fail_fast,
                inv=inv, category="wikis", name=pname, pat=cfg.pat,
            )

        if "testplans" in active:
            _safe_call(
                testplans.backup_testplans,
                bp, inv, cfg.org_url, pname,
                dry_run=cfg.dry_run, max_items=cfg.max_items,
                fail_fast=cfg.fail_fast,
                inv=inv, category="testplans", name=pname, pat=cfg.pat,
            )

    _write_indexes(bp, inv)

    # Verification (optional)
    verify_exit = 0
    if cfg.verify and not cfg.dry_run:
        try:
            from verify import verify_backup
            report = verify_backup(bp.base, cfg.org_url, pat=cfg.pat, samples=cfg.verify_samples)
            s = report.summary
            logger.info(
                "Verification: %d passed, %d failed, %d skipped, %d errors",
                s["passed"], s["failed"], s["skipped"], s["errors"],
            )
            if s["failed"] > 0:
                logger.warning(
                    "Verification failures detected – see %s",
                    bp.base / "_indexes" / "verification_report.json",
                )
                verify_exit = 2
        except Exception as exc:
            logger.error("Verification step failed: %s", exc)
            verify_exit = 2

    # Compression
    if cfg.compress and not cfg.dry_run:
        _run_compression(cfg.compress, bp)

    # Summary
    logger.info("=" * 60)
    logger.info("Backup complete: %d entities, %d errors", len(inv.entries), len(inv.errors))
    if inv.errors:
        logger.warning("Errors occurred – see %s", bp.errors_file())
    logger.info("Output: %s", bp.base)

    backup_exit = 1 if inv.errors else 0
    return max(backup_exit, verify_exit)


def _safe_call(func: Any, *args: Any, fail_fast: bool = False, inv: Inventory | None = None,
               category: str = "", name: str = "", pat: str = "", **kwargs: Any) -> None:
    """Call *func* and catch exceptions unless fail_fast is set."""
    try:
        func(*args, pat=pat, **kwargs)
    except Exception as exc:
        logger.error("%s backup failed for '%s': %s", category, name, exc)
        if inv:
            inv.add_error(category, name, str(exc), pat=pat)
        if fail_fast:
            raise


def _write_indexes(bp: BackupPaths, inv: Inventory) -> None:
    """Write manifest, inventory, and errors files."""
    try:
        inv.write(bp.inventory_file(), bp.manifest_file(), bp.errors_file())
    except Exception as exc:
        logger.error("Failed to write indexes: %s", exc)


def _run_compression(mode: str, bp: BackupPaths) -> None:
    """Apply compression based on the selected mode."""
    try:
        if mode == "repos":
            n = _compress.compress_repos(bp.projects_dir)
            logger.info("Compressed %d repo(s)", n)
        elif mode == "project":
            n = _compress.compress_projects(bp.projects_dir)
            logger.info("Compressed %d project(s)", n)
        elif mode == "all":
            archive = _compress.compress_all(bp.base)
            logger.info("Compressed entire backup → %s", archive)
    except Exception as exc:
        logger.error("Compression failed: %s", exc)
