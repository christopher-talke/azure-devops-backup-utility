"""Permissions and ACL backup."""

from __future__ import annotations

import logging
from typing import Any

import azcli
import redact
import writers
from inventory import Inventory
from paths import BackupPaths

logger = logging.getLogger(__name__)

# Security namespaces are org-wide and identical across projects.
# Cache the result after the first fetch to avoid redundant API calls.
_namespaces_exported = False


def export_security_namespaces_once(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    *,
    pat: str = "",
    timeout: int = 120,
) -> None:
    """Fetch security namespaces once (org-wide) and write to the org directory."""
    global _namespaces_exported
    if _namespaces_exported:
        return
    try:
        data = azcli.invoke(
            "security", "namespaces",
            org_url=org_url,
            timeout=timeout,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        out_path = paths.org_file("security_namespaces.json")
        writers.write_json(out_path, redact.redact(items))
        count = len(items) if isinstance(items, list) else 1
        inventory.add("permissions", "security_namespaces", str(out_path), count)
        _namespaces_exported = True
    except Exception as exc:
        logger.warning("Failed to export security namespaces: %s", exc)
        inventory.add_error("permissions", "security_namespaces", str(exc), pat=pat)


def backup_permissions(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    pat: str = "",
    dry_run: bool = False,
    timeout: int = 120,
) -> None:
    """Export project-level ACLs for a project."""
    logger.info("Backing up permissions for project '%s' …", project_name)

    if dry_run:
        logger.info("[DRY-RUN] Would export permissions for %s", project_name)
        return

    meta_dir = paths.metadata_dir(project_name)

    # Security namespaces (org-wide, fetched only once)
    export_security_namespaces_once(paths, inventory, org_url, pat=pat, timeout=timeout)

    # Project-level ACLs
    try:
        data = azcli.invoke(
            "security", "accesscontrollists",
            org_url=org_url,
            project=project_name,
            timeout=timeout,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        out_path = meta_dir / "permissions_acl.json"
        writers.write_json(out_path, redact.redact(items))
        count = len(items) if isinstance(items, list) else 1
        inventory.add("permissions", f"{project_name}/permissions_acl", str(out_path), count)
    except Exception as exc:
        logger.warning("Failed to export ACLs for '%s': %s", project_name, exc)
        inventory.add_error("permissions", f"{project_name}/permissions_acl", str(exc), pat=pat)
