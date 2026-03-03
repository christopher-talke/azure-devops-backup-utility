"""Project enumeration and metadata backup."""

from __future__ import annotations

import logging
from typing import Any

from .. import azcli, writers
from ..inventory import Inventory
from ..paths import BackupPaths

logger = logging.getLogger(__name__)


def list_projects(org_url: str) -> list[dict[str, Any]]:
    """Return the list of projects in the organisation."""
    data = azcli.az("devops", "project", "list", org_url=org_url)
    if isinstance(data, dict):
        return data.get("value", [])
    return data if isinstance(data, list) else []


def backup_project_metadata(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    dry_run: bool = False,
) -> None:
    """Export project metadata: project properties, teams, areas, iterations, permissions."""
    logger.info("Backing up metadata for project '%s' …", project_name)
    meta_dir = paths.metadata_dir(project_name)

    # Project properties
    _export_project(paths, inventory, org_url, project_name, meta_dir, dry_run=dry_run)
    # Teams
    _export_invoke(paths, inventory, org_url, project_name, meta_dir, dry_run=dry_run,
                   label="teams", area="core", resource="teams", list_key="value")
    # Areas
    _export_invoke(paths, inventory, org_url, project_name, meta_dir, dry_run=dry_run,
                   label="areas", area="wit", resource="classificationNodes",
                   route_parameters={"structureGroup": "areas"},
                   query_parameters={"$depth": "10"})
    # Iterations
    _export_invoke(paths, inventory, org_url, project_name, meta_dir, dry_run=dry_run,
                   label="iterations", area="wit", resource="classificationNodes",
                   route_parameters={"structureGroup": "iterations"},
                   query_parameters={"$depth": "10"})
    # Project-level permissions/ACL
    _export_invoke(paths, inventory, org_url, project_name, meta_dir, dry_run=dry_run,
                   label="permissions_acl", area="security", resource="accesscontrollists")


def _export_project(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    meta_dir: Any,
    *,
    dry_run: bool,
) -> None:
    if dry_run:
        logger.info("[DRY-RUN] Would export project.json for %s", project_name)
        return
    try:
        data = azcli.az("devops", "project", "show", "--project", project_name, org_url=org_url)
        out_path = meta_dir / "project.json"
        writers.write_json(out_path, data)
        inventory.add("project", project_name, str(out_path))
        logger.info("Exported project metadata for '%s'", project_name)
    except Exception as exc:
        logger.warning("Failed to export project metadata for '%s': %s", project_name, exc)
        inventory.add_error("project", project_name, str(exc))


def _export_invoke(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    meta_dir: Any,
    *,
    dry_run: bool,
    label: str,
    area: str,
    resource: str,
    list_key: str = "",
    route_parameters: dict[str, str] | None = None,
    query_parameters: dict[str, str] | None = None,
) -> None:
    filename = f"{label}.json"
    if dry_run:
        logger.info("[DRY-RUN] Would export %s for %s", filename, project_name)
        return
    try:
        data = azcli.invoke(
            area, resource,
            org_url=org_url,
            project=project_name,
            route_parameters=route_parameters,
            query_parameters=query_parameters,
        )
        items = data
        if list_key and isinstance(data, dict):
            items = data.get(list_key, data)
        out_path = meta_dir / filename
        writers.write_json(out_path, items)
        count = len(items) if isinstance(items, list) else 1
        inventory.add("project", f"{project_name}/{label}", str(out_path), count)
        logger.info("Exported %s for '%s'", label, project_name)
    except Exception as exc:
        logger.warning("Failed to export %s for '%s': %s", label, project_name, exc)
        inventory.add_error("project", f"{project_name}/{label}", str(exc))
