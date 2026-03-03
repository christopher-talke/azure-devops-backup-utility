"""Pipelines backup: definitions, classic builds, releases, runs."""

from __future__ import annotations

import logging
from typing import Any

from .. import azcli, redact, writers
from ..inventory import Inventory
from ..paths import BackupPaths

logger = logging.getLogger(__name__)


def backup_pipelines(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    dry_run: bool = False,
    max_items: int = 0,
) -> None:
    """Back up pipeline definitions, classic builds/releases, and runs index."""
    logger.info("Backing up pipelines for project '%s' …", project_name)
    pipe_dir = paths.pipelines_dir(project_name)

    _export_pipelines(pipe_dir, inventory, org_url, project_name, dry_run=dry_run)
    _export_classic_build_definitions(pipe_dir, inventory, org_url, project_name, dry_run=dry_run)
    _export_classic_release_definitions(pipe_dir, inventory, org_url, project_name, dry_run=dry_run)
    _export_runs_index(pipe_dir, inventory, org_url, project_name, dry_run=dry_run, max_items=max_items)


def _export_pipelines(
    pipe_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    dry_run: bool,
) -> None:
    if dry_run:
        logger.info("[DRY-RUN] Would export pipelines for %s", project_name)
        return
    try:
        data = azcli.az("pipelines", "list", org_url=org_url, project=project_name)
        items = data if isinstance(data, list) else (data.get("value", []) if isinstance(data, dict) else [])
        out_path = pipe_dir / "pipelines.json"
        writers.write_json(out_path, items)
        inventory.add("pipelines", f"{project_name}/pipelines", str(out_path), len(items))
        logger.info("Exported %d pipeline definitions for '%s'", len(items), project_name)
    except Exception as exc:
        logger.warning("Failed to export pipelines for '%s': %s", project_name, exc)
        inventory.add_error("pipelines", f"{project_name}/pipelines", str(exc))


def _export_classic_build_definitions(
    pipe_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    dry_run: bool,
) -> None:
    if dry_run:
        logger.info("[DRY-RUN] Would export classic build definitions for %s", project_name)
        return
    try:
        data = azcli.invoke(
            "build", "definitions",
            org_url=org_url,
            project=project_name,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        items = redact.redact(items)
        out_path = pipe_dir / "classic_build_definitions.json"
        writers.write_json(out_path, items)
        count = len(items) if isinstance(items, list) else 1
        inventory.add("pipelines", f"{project_name}/classic_build_definitions", str(out_path), count)
    except Exception as exc:
        logger.warning("Failed to export classic build definitions for '%s': %s", project_name, exc)
        inventory.add_error("pipelines", f"{project_name}/classic_build_definitions", str(exc))


def _export_classic_release_definitions(
    pipe_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    dry_run: bool,
) -> None:
    if dry_run:
        logger.info("[DRY-RUN] Would export classic release definitions for %s", project_name)
        return
    try:
        data = azcli.invoke(
            "release", "definitions",
            org_url=org_url,
            project=project_name,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        items = redact.redact(items)
        out_path = pipe_dir / "classic_release_definitions.json"
        writers.write_json(out_path, items)
        count = len(items) if isinstance(items, list) else 1
        inventory.add("pipelines", f"{project_name}/classic_release_definitions", str(out_path), count)
    except Exception as exc:
        logger.warning("Failed to export classic release definitions for '%s': %s", project_name, exc)
        inventory.add_error("pipelines", f"{project_name}/classic_release_definitions", str(exc))


def _export_runs_index(
    pipe_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    dry_run: bool,
    max_items: int = 0,
) -> None:
    if dry_run:
        logger.info("[DRY-RUN] Would export pipeline runs index for %s", project_name)
        return
    try:
        qp: dict[str, str] = {}
        if max_items:
            qp["$top"] = str(max_items)
        data = azcli.invoke(
            "build", "builds",
            org_url=org_url,
            project=project_name,
            query_parameters=qp if qp else None,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        out_path = pipe_dir / "runs_index.json"
        writers.write_json(out_path, items)
        count = len(items) if isinstance(items, list) else 1
        inventory.add("pipelines", f"{project_name}/runs_index", str(out_path), count)
    except Exception as exc:
        logger.warning("Failed to export pipeline runs index for '%s': %s", project_name, exc)
        inventory.add_error("pipelines", f"{project_name}/runs_index", str(exc))
