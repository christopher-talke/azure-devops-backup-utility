"""Boards backup: work items, queries, tags."""

from __future__ import annotations

import logging
from typing import Any

from .. import azcli, writers
from ..inventory import Inventory
from ..paths import BackupPaths

logger = logging.getLogger(__name__)


def backup_boards(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    dry_run: bool = False,
    max_items: int = 0,
) -> None:
    """Back up work items, queries, and tags for a project."""
    logger.info("Backing up boards for project '%s' …", project_name)
    boards_dir = paths.boards_dir(project_name)

    _export_queries(boards_dir, inventory, org_url, project_name, dry_run=dry_run)
    _export_tags(boards_dir, inventory, org_url, project_name, dry_run=dry_run)
    _export_work_items(paths, inventory, org_url, project_name, dry_run=dry_run, max_items=max_items)


def _export_queries(
    boards_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    dry_run: bool,
) -> None:
    if dry_run:
        logger.info("[DRY-RUN] Would export queries for %s", project_name)
        return
    try:
        data = azcli.invoke(
            "wit", "queries",
            org_url=org_url,
            project=project_name,
            query_parameters={"$depth": "2"},
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        out_path = boards_dir / "queries.json"
        writers.write_json(out_path, items)
        count = len(items) if isinstance(items, list) else 1
        inventory.add("boards", f"{project_name}/queries", str(out_path), count)
    except Exception as exc:
        logger.warning("Failed to export queries for '%s': %s", project_name, exc)
        inventory.add_error("boards", f"{project_name}/queries", str(exc))


def _export_tags(
    boards_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    dry_run: bool,
) -> None:
    if dry_run:
        logger.info("[DRY-RUN] Would export tags for %s", project_name)
        return
    try:
        data = azcli.invoke(
            "wit", "tags",
            org_url=org_url,
            project=project_name,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        out_path = boards_dir / "tags.json"
        writers.write_json(out_path, items)
        count = len(items) if isinstance(items, list) else 1
        inventory.add("boards", f"{project_name}/tags", str(out_path), count)
    except Exception as exc:
        logger.warning("Failed to export tags for '%s': %s", project_name, exc)
        inventory.add_error("boards", f"{project_name}/tags", str(exc))


def _export_work_items(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    dry_run: bool,
    max_items: int = 0,
) -> None:
    """Export work items using WIQL query via az devops invoke."""
    if dry_run:
        logger.info("[DRY-RUN] Would export work items for %s", project_name)
        return

    wi_dir = paths.work_items_dir(project_name)

    # Get work item IDs via a flat WIQL query
    try:
        wiql_result = azcli.az(
            "boards", "query",
            "--wiql", "SELECT [System.Id] FROM WorkItems ORDER BY [System.Id]",
            org_url=org_url,
            project=project_name,
        )
    except Exception as exc:
        logger.warning("Failed to query work items for '%s': %s", project_name, exc)
        inventory.add_error("boards", f"{project_name}/work_items", str(exc))
        return

    work_items = wiql_result if isinstance(wiql_result, list) else []
    if isinstance(wiql_result, dict):
        work_items = wiql_result.get("workItems", wiql_result.get("value", []))

    ids = [wi.get("id") for wi in work_items if wi.get("id")]
    if max_items:
        ids = ids[:max_items]

    # Write index
    writers.write_json(wi_dir / "index.json", {"count": len(ids), "ids": ids})
    inventory.add("boards", f"{project_name}/work_items", str(wi_dir / "index.json"), len(ids))
    logger.info("Found %d work items for '%s'", len(ids), project_name)

    # Export individual work items in batches
    batch_size = 200
    for batch_start in range(0, len(ids), batch_size):
        batch_ids = ids[batch_start: batch_start + batch_size]
        try:
            ids_str = ",".join(str(i) for i in batch_ids)
            items = azcli.az(
                "boards", "work-item", "show",
                "--id", ids_str,
                "--expand", "all",
                org_url=org_url,
                project=project_name,
            )
            if isinstance(items, dict):
                items = [items]
            if isinstance(items, list):
                for item in items:
                    wi_id = item.get("id", "unknown")
                    writers.write_json(wi_dir / f"{wi_id}.json", item)
        except Exception as exc:
            logger.warning("Failed to export work items batch starting at %d: %s", batch_start, exc)
            inventory.add_error("boards", f"{project_name}/work_items/batch_{batch_start}", str(exc))
