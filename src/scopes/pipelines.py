"""Pipelines backup: definitions, runs, environments, secure files, task groups, releases."""

from __future__ import annotations

import logging
from typing import Any

import azcli
import redact
import writers
from inventory import Inventory
from paths import BackupPaths

logger = logging.getLogger(__name__)


def backup_pipelines(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    pat: str = "",
    dry_run: bool = False,
    max_items: int = 0,
    since: str = "",
) -> None:
    """Back up pipeline definitions and runs index."""
    logger.info("Backing up pipelines for project '%s' …", project_name)
    pipe_dir = paths.pipelines_dir(project_name)

    _export_pipelines(pipe_dir, inventory, org_url, project_name, dry_run=dry_run, pat=pat)
    _export_runs_index(pipe_dir, inventory, org_url, project_name, dry_run=dry_run, max_items=max_items, pat=pat, since=since)
    _export_environments(pipe_dir, inventory, org_url, project_name, dry_run=dry_run, pat=pat)
    _export_secure_files(pipe_dir, inventory, org_url, project_name, dry_run=dry_run, pat=pat)
    _export_task_groups(pipe_dir, inventory, org_url, project_name, dry_run=dry_run, pat=pat)
    _export_release_definitions(pipe_dir, inventory, org_url, project_name, dry_run=dry_run, pat=pat)


def _export_pipelines(
    pipe_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    dry_run: bool,
    pat: str = "",
) -> None:
    if dry_run:
        logger.info("[DRY-RUN] Would export pipelines for %s", project_name)
        return
    try:
        data = azcli.az("pipelines", "list", org_url=org_url, project=project_name)
        items = data if isinstance(data, list) else (data.get("value", []) if isinstance(data, dict) else [])
        out_path = pipe_dir / "pipelines.json"
        writers.write_json(out_path, redact.redact(items))
        inventory.add("pipelines", f"{project_name}/pipelines", str(out_path), len(items))
        logger.info("Exported %d pipeline definitions for '%s'", len(items), project_name)
    except Exception as exc:
        logger.warning("Failed to export pipelines for '%s': %s", project_name, exc)
        inventory.add_error("pipelines", f"{project_name}/pipelines", str(exc), pat=pat)


def _export_runs_index(
    pipe_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    dry_run: bool,
    max_items: int = 0,
    pat: str = "",
    since: str = "",
) -> None:
    if dry_run:
        logger.info("[DRY-RUN] Would export pipeline runs index for %s", project_name)
        return
    try:
        qp: dict[str, str] = {}
        if max_items:
            qp["$top"] = str(max_items)
        if since:
            qp["minTime"] = since
        data = azcli.invoke(
            "build", "builds",
            org_url=org_url,
            project=project_name,
            query_parameters=qp if qp else None,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        out_path = pipe_dir / "runs_index.json"
        writers.write_json(out_path, redact.redact(items))
        count = len(items) if isinstance(items, list) else 1
        inventory.add("pipelines", f"{project_name}/runs_index", str(out_path), count)
    except Exception as exc:
        logger.warning("Failed to export pipeline runs index for '%s': %s", project_name, exc)
        inventory.add_error("pipelines", f"{project_name}/runs_index", str(exc), pat=pat)


def _export_environments(
    pipe_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    dry_run: bool,
    pat: str = "",
) -> None:
    """Export pipeline environments and their check configurations."""
    if dry_run:
        logger.info("[DRY-RUN] Would export pipeline environments for %s", project_name)
        return
    try:
        data = azcli.invoke(
            "distributedtask", "environments",
            org_url=org_url,
            project=project_name,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        out_path = pipe_dir / "environments.json"
        writers.write_json(out_path, redact.redact(items))
        count = len(items) if isinstance(items, list) else 1
        inventory.add("pipelines", f"{project_name}/environments", str(out_path), count)
        logger.info("Exported %d environment(s) for '%s'", count, project_name)
    except Exception as exc:
        logger.warning("Failed to export pipeline environments for '%s': %s", project_name, exc)
        inventory.add_error("pipelines", f"{project_name}/environments", str(exc), pat=pat)


def _export_secure_files(
    pipe_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    dry_run: bool,
    pat: str = "",
) -> None:
    """Export secure file metadata (names only, never contents)."""
    if dry_run:
        logger.info("[DRY-RUN] Would export secure files metadata for %s", project_name)
        return
    try:
        data = azcli.invoke(
            "distributedtask", "securefiles",
            org_url=org_url,
            project=project_name,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        out_path = pipe_dir / "secure_files.json"
        writers.write_json(out_path, redact.redact(items))
        count = len(items) if isinstance(items, list) else 1
        inventory.add("pipelines", f"{project_name}/secure_files", str(out_path), count)
        logger.info("Exported %d secure file(s) metadata for '%s'", count, project_name)
    except Exception as exc:
        logger.warning("Failed to export secure files for '%s': %s", project_name, exc)
        inventory.add_error("pipelines", f"{project_name}/secure_files", str(exc), pat=pat)


def _export_task_groups(
    pipe_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    dry_run: bool,
    pat: str = "",
) -> None:
    """Export classic task groups."""
    if dry_run:
        logger.info("[DRY-RUN] Would export task groups for %s", project_name)
        return
    try:
        data = azcli.invoke(
            "distributedtask", "taskgroups",
            org_url=org_url,
            project=project_name,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        out_path = pipe_dir / "task_groups.json"
        writers.write_json(out_path, redact.redact(items))
        count = len(items) if isinstance(items, list) else 1
        inventory.add("pipelines", f"{project_name}/task_groups", str(out_path), count)
        logger.info("Exported %d task group(s) for '%s'", count, project_name)
    except Exception as exc:
        logger.warning("Failed to export task groups for '%s': %s", project_name, exc)
        inventory.add_error("pipelines", f"{project_name}/task_groups", str(exc), pat=pat)


def _export_release_definitions(
    pipe_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    dry_run: bool,
    pat: str = "",
) -> None:
    """Export classic release definitions.

    Note: release definitions use the vsrm subdomain in direct REST calls,
    but ``az devops invoke`` routes via the standard endpoint. If the area
    is not registered the call will fail gracefully.
    """
    if dry_run:
        logger.info("[DRY-RUN] Would export release definitions for %s", project_name)
        return
    try:
        data = azcli.invoke(
            "release", "definitions",
            org_url=org_url,
            project=project_name,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        out_path = pipe_dir / "release_definitions.json"
        writers.write_json(out_path, redact.redact(items))
        count = len(items) if isinstance(items, list) else 1
        inventory.add("pipelines", f"{project_name}/release_definitions", str(out_path), count)
        logger.info("Exported %d release definition(s) for '%s'", count, project_name)
    except Exception as exc:
        logger.warning("Failed to export release definitions for '%s': %s", project_name, exc)
        inventory.add_error("pipelines", f"{project_name}/release_definitions", str(exc), pat=pat)
