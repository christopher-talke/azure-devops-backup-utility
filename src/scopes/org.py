"""Organisation-level backup: users, groups, service connections, service principals, PATs."""

from __future__ import annotations

import logging
from typing import Any

import azcli
import redact
import writers
from inventory import Inventory
from paths import BackupPaths

logger = logging.getLogger(__name__)


def backup_org(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    *,
    pat: str = "",
    dry_run: bool = False,
    timeout: int = 120,
) -> None:
    """Export organisation-scoped entities."""
    logger.info("Backing up organisation-level data …")

    _export(paths, inventory, org_url, dry_run=dry_run, pat=pat, timeout=timeout, label="users",
            area="graph", resource="users",
            query_parameters={"subjectTypes": "aad,msa"}, list_key="value")
    _export(paths, inventory, org_url, dry_run=dry_run, pat=pat, timeout=timeout, label="groups",
            area="graph", resource="groups", list_key="value")
    _export(paths, inventory, org_url, dry_run=dry_run, pat=pat, timeout=timeout, label="memberships",
            area="graph", resource="memberships", list_key="value",
            api_version="7.1-preview.1")
    _export_service_connections(paths, inventory, org_url, dry_run=dry_run, pat=pat, timeout=timeout)
    _export_variable_groups(paths, inventory, org_url, dry_run=dry_run, pat=pat, timeout=timeout)
    _export(paths, inventory, org_url, dry_run=dry_run, pat=pat, timeout=timeout, label="agent_pools",
            area="distributedtask", resource="pools", list_key="value")
    _export(paths, inventory, org_url, dry_run=dry_run, pat=pat, timeout=timeout, label="queues",
            area="distributedtask", resource="queues", list_key="value")
    _export_permissions_acl(paths, inventory, org_url, dry_run=dry_run, pat=pat, timeout=timeout)
    _export(paths, inventory, org_url, dry_run=dry_run, pat=pat, timeout=timeout, label="service_principals",
            area="graph", resource="serviceprincipals", list_key="value")
    _export_pat_tokens(paths, inventory, org_url, dry_run=dry_run, pat=pat, timeout=timeout)


def _export(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    *,
    dry_run: bool,
    pat: str = "",
    timeout: int = 120,
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
            timeout=timeout,
        )
        items = data.get(list_key, data) if isinstance(data, dict) else data
        items = redact.redact(items)
        out_path = paths.org_file(filename)
        writers.write_json(out_path, items)
        count = len(items) if isinstance(items, list) else 1
        inventory.add("org", label, str(out_path), count)
        logger.info("Exported %s (%d items)", label, count)
    except Exception as exc:
        logger.warning("Failed to export %s: %s", label, exc)
        inventory.add_error("org", label, str(exc), pat=pat)


def _export_service_connections(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    *,
    dry_run: bool,
    pat: str = "",
    timeout: int = 120,
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
            timeout=timeout,
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
        inventory.add_error("org", label, str(exc), pat=pat)


def _export_variable_groups(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    *,
    dry_run: bool,
    pat: str = "",
    timeout: int = 120,
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
            timeout=timeout,
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
        inventory.add_error("org", label, str(exc), pat=pat)


def _export_permissions_acl(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    *,
    dry_run: bool,
    pat: str = "",
    timeout: int = 120,
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
            timeout=timeout,
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
        inventory.add_error("org", label, str(exc), pat=pat)


def _export_pat_tokens(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    *,
    dry_run: bool,
    pat: str = "",
    timeout: int = 120,
) -> None:
    """Export PAT token metadata for the authenticated user.

    Token values are redacted; only metadata (display name, scope, expiry) is kept.
    This endpoint may not be available in all org configurations.
    """
    label = "pat_tokens"
    filename = f"{label}.json"
    if dry_run:
        logger.info("[DRY-RUN] Would export %s", filename)
        return
    try:
        data = azcli.invoke(
            "tokens", "pats",
            org_url=org_url,
            timeout=timeout,
        )
        items = data.get("patTokens", data.get("value", data)) if isinstance(data, dict) else data
        if not isinstance(items, list):
            items = [items] if items else []
        items = redact.redact(items)
        out_path = paths.org_file(filename)
        writers.write_json(out_path, items)
        inventory.add("org", label, str(out_path), len(items))
        logger.info("Exported %s (%d items)", label, len(items))
    except Exception as exc:
        logger.warning("Failed to export %s: %s", label, exc)
        inventory.add_error("org", label, str(exc), pat=pat)
