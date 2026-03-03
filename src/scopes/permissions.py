"""Permissions and ACL backup."""

from __future__ import annotations

import logging
from typing import Any

import azcli
import writers
from inventory import Inventory
from paths import BackupPaths

logger = logging.getLogger(__name__)


def backup_permissions(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    dry_run: bool = False,
) -> None:
    """Export security namespaces and ACLs for a project."""
    logger.info("Backing up permissions for project '%s' …", project_name)

    if dry_run:
        logger.info("[DRY-RUN] Would export permissions for %s", project_name)
        return

    meta_dir = paths.metadata_dir(project_name)

    # Security namespaces
    try:
        data = azcli.invoke(
            "security", "namespaces",
            org_url=org_url,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        out_path = meta_dir / "security_namespaces.json"
        writers.write_json(out_path, items)
        count = len(items) if isinstance(items, list) else 1
        inventory.add("permissions", f"{project_name}/security_namespaces", str(out_path), count)
    except Exception as exc:
        logger.warning("Failed to export security namespaces for '%s': %s", project_name, exc)
        inventory.add_error("permissions", f"{project_name}/security_namespaces", str(exc))

    # Project-level ACLs
    try:
        data = azcli.invoke(
            "security", "accesscontrollists",
            org_url=org_url,
            project=project_name,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        out_path = meta_dir / "permissions_acl.json"
        writers.write_json(out_path, items)
        count = len(items) if isinstance(items, list) else 1
        inventory.add("permissions", f"{project_name}/permissions_acl", str(out_path), count)
    except Exception as exc:
        logger.warning("Failed to export ACLs for '%s': %s", project_name, exc)
        inventory.add_error("permissions", f"{project_name}/permissions_acl", str(exc))
