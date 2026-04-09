"""Boards backup: work items, queries, tags."""

from __future__ import annotations

import logging
from typing import Any

import azcli
import redact
import writers
from inventory import Inventory
from paths import BackupPaths, safe_name

logger = logging.getLogger(__name__)


def backup_boards(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    pat: str = "",
    dry_run: bool = False,
    max_items: int = 0,
    since: str = "",
    timeout: int = 120,
) -> None:
    """Back up work items, queries, and tags for a project."""
    logger.info("Backing up boards for project '%s' …", project_name)
    boards_dir = paths.boards_dir(project_name)

    _export_queries(boards_dir, inventory, org_url, project_name, dry_run=dry_run, pat=pat, timeout=timeout)
    _export_tags(boards_dir, inventory, org_url, project_name, dry_run=dry_run, pat=pat, timeout=timeout)
    _export_work_items(paths, inventory, org_url, project_name, dry_run=dry_run, max_items=max_items, pat=pat, since=since, timeout=timeout)
    _export_board_config(boards_dir, inventory, org_url, project_name, dry_run=dry_run, pat=pat, timeout=timeout)
    _export_team_settings(boards_dir, inventory, org_url, project_name, dry_run=dry_run, pat=pat, timeout=timeout)


def _export_queries(
    boards_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    dry_run: bool,
    pat: str = "",
    timeout: int = 120,
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
            timeout=timeout,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        out_path = boards_dir / "queries.json"
        writers.write_json(out_path, redact.redact(items))
        count = len(items) if isinstance(items, list) else 1
        inventory.add("boards", f"{project_name}/queries", str(out_path), count)
    except Exception as exc:
        logger.warning("Failed to export queries for '%s': %s", project_name, exc)
        inventory.add_error("boards", f"{project_name}/queries", str(exc), pat=pat)


def _export_tags(
    boards_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    dry_run: bool,
    pat: str = "",
    timeout: int = 120,
) -> None:
    if dry_run:
        logger.info("[DRY-RUN] Would export tags for %s", project_name)
        return
    try:
        data = azcli.invoke(
            "wit", "tags",
            org_url=org_url,
            project=project_name,
            timeout=timeout,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        out_path = boards_dir / "tags.json"
        writers.write_json(out_path, redact.redact(items))
        count = len(items) if isinstance(items, list) else 1
        inventory.add("boards", f"{project_name}/tags", str(out_path), count)
    except Exception as exc:
        logger.warning("Failed to export tags for '%s': %s", project_name, exc)
        inventory.add_error("boards", f"{project_name}/tags", str(exc), pat=pat)


def _export_work_items(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    dry_run: bool,
    max_items: int = 0,
    pat: str = "",
    since: str = "",
    timeout: int = 120,
) -> None:
    """Export work items using WIQL query via az devops invoke."""
    if dry_run:
        logger.info("[DRY-RUN] Would export work items for %s", project_name)
        return

    wi_dir = paths.work_items_dir(project_name)

    # Get work item IDs via a flat WIQL query
    wiql = "SELECT [System.Id] FROM WorkItems"
    if since:
        wiql += f" WHERE [System.ChangedDate] >= '{since}'"
    wiql += " ORDER BY [System.Id]"
    try:
        wiql_result = azcli.az(
            "boards", "query",
            "--wiql", wiql,
            org_url=org_url,
            project=project_name,
            timeout=timeout,
        )
    except Exception as exc:
        logger.warning("Failed to query work items for '%s': %s", project_name, exc)
        inventory.add_error("boards", f"{project_name}/work_items", str(exc), pat=pat)
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

    # Export individual work items in batches (per-item fetch for reliability)
    batch_size = 200
    for batch_start in range(0, len(ids), batch_size):
        batch_ids = ids[batch_start: batch_start + batch_size]
        for wi_id in batch_ids:
            try:
                item = azcli.invoke(
                    "wit", "workItems",
                    route_parameters={"id": str(wi_id)},
                    query_parameters={"$expand": "all"},
                    org_url=org_url,
                    project=project_name,
                    paginate=False,
                    timeout=timeout,
                )
                if not isinstance(item, dict):
                    logger.warning("Unexpected response for work item %d, skipping", wi_id)
                    continue
                writers.write_json(wi_dir / f"{wi_id}.json", redact.redact(item))
                _export_work_item_revisions(wi_dir, inventory, org_url, project_name,
                                            wi_id, pat=pat)
                _export_work_item_attachments(paths, inventory, project_name, wi_id,
                                              item, pat=pat)
            except Exception as exc:
                logger.warning("Failed to export work item %d: %s", wi_id, exc)
                inventory.add_error("boards", f"{project_name}/work_items/{wi_id}", str(exc), pat=pat)


def _export_work_item_revisions(
    wi_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    wi_id: int,
    *,
    pat: str = "",
) -> None:
    """Export full revision history for a single work item."""
    try:
        data = azcli.invoke(
            "wit", "revisions",
            org_url=org_url,
            project=project_name,
            route_parameters={"id": str(wi_id)},
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            items = [items] if items else []
        writers.write_json(wi_dir / f"{wi_id}_revisions.json", redact.redact(items))
    except Exception as exc:
        logger.debug("Could not export revisions for work item %d in '%s': %s",
                      wi_id, project_name, exc)


def _export_work_item_attachments(
    paths: BackupPaths,
    inventory: Inventory,
    project_name: str,
    wi_id: int,
    item: dict,
    *,
    pat: str = "",
) -> None:
    """Download binary attachments for a single work item."""
    relations = item.get("relations") or []
    attach_dir = paths.work_item_attachments_dir(project_name, wi_id)
    for rel in relations:
        if rel.get("rel") != "AttachedFile":
            continue
        url = rel.get("url", "")
        filename = safe_name(rel.get("attributes", {}).get("name", "attachment"))
        if not url or not filename:
            continue
        dest = attach_dir / filename
        try:
            azcli.download_binary(url, dest)
            inventory.add("boards", f"{project_name}/work_items/{wi_id}/attachments/{filename}",
                           str(dest))
            logger.debug("Downloaded attachment '%s' for work item %d", filename, wi_id)
        except Exception as exc:
            logger.debug("Could not download attachment '%s' for work item %d: %s",
                          filename, wi_id, exc)


def _export_board_config(
    boards_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    dry_run: bool,
    pat: str = "",
    timeout: int = 120,
) -> None:
    """Export board definitions including columns and rows (swimlanes)."""
    if dry_run:
        logger.info("[DRY-RUN] Would export board config for %s", project_name)
        return
    try:
        data = azcli.invoke(
            "work", "boards",
            org_url=org_url,
            project=project_name,
            timeout=timeout,
        )
        boards = data.get("value", data) if isinstance(data, dict) else data
        if not isinstance(boards, list):
            boards = [boards] if boards else []
        out_path = boards_dir / "board_config.json"
        writers.write_json(out_path, redact.redact(boards))
        inventory.add("boards", f"{project_name}/board_config", str(out_path), len(boards))
        logger.info("Exported %d board(s) config for '%s'", len(boards), project_name)

        # Export columns and rows per board
        for board in boards:
            board_id = board.get("id", "")
            board_name = board.get("name", "unknown")
            if not board_id:
                continue
            # Columns
            try:
                col_data = azcli.invoke(
                    "work", "boardcolumns",
                    org_url=org_url,
                    project=project_name,
                    route_parameters={"board": board_id},
                    paginate=False,
                )
                cols = col_data.get("value", col_data) if isinstance(col_data, dict) else col_data
                writers.write_json(boards_dir / f"board_{board_name}_columns.json", redact.redact(cols))
            except Exception as exc:
                logger.debug("Could not export columns for board '%s': %s", board_name, exc)
            # Rows (swimlanes)
            try:
                row_data = azcli.invoke(
                    "work", "boardrows",
                    org_url=org_url,
                    project=project_name,
                    route_parameters={"board": board_id},
                    paginate=False,
                )
                rows = row_data.get("value", row_data) if isinstance(row_data, dict) else row_data
                writers.write_json(boards_dir / f"board_{board_name}_rows.json", redact.redact(rows))
            except Exception as exc:
                logger.debug("Could not export rows for board '%s': %s", board_name, exc)

    except Exception as exc:
        logger.warning("Failed to export board config for '%s': %s", project_name, exc)
        inventory.add_error("boards", f"{project_name}/board_config", str(exc), pat=pat)


def _export_team_settings(
    boards_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    dry_run: bool,
    pat: str = "",
    timeout: int = 120,
) -> None:
    """Export team settings and iteration capacities."""
    if dry_run:
        logger.info("[DRY-RUN] Would export team settings for %s", project_name)
        return
    try:
        data = azcli.invoke(
            "work", "teamsettings",
            org_url=org_url,
            project=project_name,
            paginate=False,
            timeout=timeout,
        )
        out_path = boards_dir / "team_settings.json"
        writers.write_json(out_path, redact.redact(data))
        inventory.add("boards", f"{project_name}/team_settings", str(out_path))
        logger.info("Exported team settings for '%s'", project_name)
    except Exception as exc:
        logger.warning("Failed to export team settings for '%s': %s", project_name, exc)
        inventory.add_error("boards", f"{project_name}/team_settings", str(exc), pat=pat)

    # Team iterations
    try:
        data = azcli.invoke(
            "work", "iterations",
            org_url=org_url,
            project=project_name,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        out_path = boards_dir / "team_iterations.json"
        writers.write_json(out_path, redact.redact(items))
        count = len(items) if isinstance(items, list) else 1
        inventory.add("boards", f"{project_name}/team_iterations", str(out_path), count)
    except Exception as exc:
        logger.warning("Failed to export team iterations for '%s': %s", project_name, exc)
        inventory.add_error("boards", f"{project_name}/team_iterations", str(exc), pat=pat)
