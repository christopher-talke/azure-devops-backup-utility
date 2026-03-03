"""Organisation-level backup: users, groups, service connections, etc."""

from __future__ import annotations

import logging
from typing import Any

from .. import azcli, redact, writers
from ..inventory import Inventory
from ..paths import BackupPaths

logger = logging.getLogger(__name__)


def backup_org(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    *,
    dry_run: bool = False,
) -> None:
    """Export organisation-scoped entities."""
    logger.info("Backing up organisation-level data …")

    _export(paths, inventory, org_url, dry_run=dry_run, label="users",
            area="graph", resource="users",
            query_parameters={"subjectTypes": "aad,msa"}, list_key="value")
    _export(paths, inventory, org_url, dry_run=dry_run, label="groups",
            area="graph", resource="groups", list_key="value")
    _export(paths, inventory, org_url, dry_run=dry_run, label="memberships",
            area="graph", resource="memberships", list_key="value",
            api_version="7.1-preview.1")
    _export_service_connections(paths, inventory, org_url, dry_run=dry_run)
    _export_variable_groups(paths, inventory, org_url, dry_run=dry_run)
    _export(paths, inventory, org_url, dry_run=dry_run, label="agent_pools",
            area="distributedtask", resource="pools", list_key="value")
    _export(paths, inventory, org_url, dry_run=dry_run, label="queues",
            area="distributedtask", resource="queues", list_key="value")
    _export_permissions_acl(paths, inventory, org_url, dry_run=dry_run)


def _export(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    *,
    dry_run: bool,
    label: str,
    area: str,
    resource: str,
    list_key: str = "value",
    query_parameters: dict[str, str] | None = None,
    api_version: str = "",
) -> None:
    """Generic helper to invoke and persist a single resource list."""
    filename = f"{label}.json"
    if dry_run:
        logger.info("[DRY-RUN] Would export %s", filename)
        return
    try:
        data = azcli.invoke(
            area, resource,
            org_url=org_url,
            query_parameters=query_parameters or {},
            api_version=api_version,
        )
        items = data.get(list_key, data) if isinstance(data, dict) else data
        out_path = paths.org_file(filename)
        writers.write_json(out_path, items)
        count = len(items) if isinstance(items, list) else 1
        inventory.add("org", label, str(out_path), count)
        logger.info("Exported %s (%d items)", label, count)
    except Exception as exc:
        logger.warning("Failed to export %s: %s", label, exc)
        inventory.add_error("org", label, str(exc))


def _export_service_connections(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    *,
    dry_run: bool,
) -> None:
    label = "service_connections"
    filename = f"{label}.json"
    if dry_run:
        logger.info("[DRY-RUN] Would export %s", filename)
        return
    try:
        data = azcli.invoke(
            "serviceendpoint", "endpoints",
            org_url=org_url,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        items = redact.redact(items)
        out_path = paths.org_file(filename)
        writers.write_json(out_path, items)
        count = len(items) if isinstance(items, list) else 1
        inventory.add("org", label, str(out_path), count)
        logger.info("Exported %s (%d items)", label, count)
    except Exception as exc:
        logger.warning("Failed to export %s: %s", label, exc)
        inventory.add_error("org", label, str(exc))


def _export_variable_groups(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    *,
    dry_run: bool,
) -> None:
    label = "variable_groups"
    filename = f"{label}.json"
    if dry_run:
        logger.info("[DRY-RUN] Would export %s", filename)
        return
    try:
        data = azcli.invoke(
            "distributedtask", "variablegroups",
            org_url=org_url,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        items = redact.redact(items)
        out_path = paths.org_file(filename)
        writers.write_json(out_path, items)
        count = len(items) if isinstance(items, list) else 1
        inventory.add("org", label, str(out_path), count)
        logger.info("Exported %s (%d items)", label, count)
    except Exception as exc:
        logger.warning("Failed to export %s: %s", label, exc)
        inventory.add_error("org", label, str(exc))


def _export_permissions_acl(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    *,
    dry_run: bool,
) -> None:
    label = "permissions_acl"
    filename = f"{label}.json"
    if dry_run:
        logger.info("[DRY-RUN] Would export %s", filename)
        return
    try:
        data = azcli.invoke(
            "security", "accesscontrollists",
            org_url=org_url,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        out_path = paths.org_file(filename)
        writers.write_json(out_path, items)
        count = len(items) if isinstance(items, list) else 1
        inventory.add("org", label, str(out_path), count)
        logger.info("Exported %s (%d items)", label, count)
    except Exception as exc:
        logger.warning("Failed to export %s: %s", label, exc)
        inventory.add_error("org", label, str(exc))
