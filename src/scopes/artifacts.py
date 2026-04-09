"""Artifacts / Azure Feeds backup: feed configs, package metadata, permissions, retention."""

from __future__ import annotations

import logging
from typing import Any

import azcli
import redact
import writers
from inventory import Inventory
from paths import BackupPaths

logger = logging.getLogger(__name__)


def backup_artifacts(
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
    """Back up Azure Artifacts feeds and package metadata for a project.

    *since* is accepted for API consistency but not currently used — the
    Azure Artifacts API does not support date-based filtering.
    """
    logger.info("Backing up artifacts for project '%s' …", project_name)

    if dry_run:
        logger.info("[DRY-RUN] Would export artifacts for %s", project_name)
        return

    art_dir = paths.artifacts_dir(project_name)

    # Feeds
    try:
        data = azcli.invoke(
            "packaging", "feeds",
            org_url=org_url,
            project=project_name,
            timeout=timeout,
        )
        feeds = data.get("value", data) if isinstance(data, dict) else data
        if not isinstance(feeds, list):
            feeds = [feeds] if feeds else []

        writers.write_json(art_dir / "feeds.json", redact.redact(feeds))
        inventory.add("artifacts", f"{project_name}/feeds",
                       str(art_dir / "feeds.json"), len(feeds))
        logger.info("Exported %d feed(s) for '%s'", len(feeds), project_name)

        # Package metadata, permissions, and retention per feed
        for feed in feeds:
            feed_id = feed.get("id", "")
            feed_name = feed.get("name", "unknown")
            if not feed_id:
                continue
            _export_feed_packages(art_dir, inventory, org_url, project_name,
                                  feed_id, feed_name, pat=pat, max_items=max_items)
            _export_feed_permissions(art_dir, inventory, org_url, project_name,
                                     feed_id, feed_name, pat=pat)
            _export_feed_retention(art_dir, inventory, org_url, project_name,
                                   feed_id, feed_name, pat=pat)

    except Exception as exc:
        logger.warning("Failed to export feeds for '%s': %s", project_name, exc)
        inventory.add_error("artifacts", f"{project_name}/feeds", str(exc), pat=pat)


def _export_feed_packages(
    art_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    feed_id: str,
    feed_name: str,
    *,
    pat: str = "",
    max_items: int = 0,
) -> None:
    """Export package metadata (not binaries) for a single feed."""
    try:
        qp: dict[str, str] = {}
        if max_items:
            qp["$top"] = str(max_items)
        data = azcli.invoke(
            "packaging", "packages",
            org_url=org_url,
            project=project_name,
            route_parameters={"feedId": feed_id},
            query_parameters=qp if qp else None,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            items = [items] if items else []
        out_path = art_dir / f"feed_{feed_name}_packages.json"
        writers.write_json(out_path, redact.redact(items))
        inventory.add("artifacts", f"{project_name}/feeds/{feed_name}/packages",
                       str(out_path), len(items))
        logger.info("Exported %d packages for feed '%s'", len(items), feed_name)
    except Exception as exc:
        logger.warning("Failed to export packages for feed '%s': %s", feed_name, exc)
        inventory.add_error("artifacts", f"{project_name}/feeds/{feed_name}/packages",
                            str(exc), pat=pat)


def _export_feed_permissions(
    art_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    feed_id: str,
    feed_name: str,
    *,
    pat: str = "",
) -> None:
    """Export permissions for a single feed."""
    try:
        data = azcli.invoke(
            "packaging", "feedpermissions",
            org_url=org_url,
            project=project_name,
            route_parameters={"feedId": feed_id},
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            items = [items] if items else []
        out_path = art_dir / f"feed_{feed_name}_permissions.json"
        writers.write_json(out_path, redact.redact(items))
        inventory.add("artifacts", f"{project_name}/feeds/{feed_name}/permissions",
                       str(out_path), len(items))
        logger.info("Exported %d permission(s) for feed '%s'", len(items), feed_name)
    except Exception as exc:
        logger.warning("Failed to export permissions for feed '%s': %s", feed_name, exc)
        inventory.add_error("artifacts", f"{project_name}/feeds/{feed_name}/permissions",
                            str(exc), pat=pat)


def _export_feed_retention(
    art_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    feed_id: str,
    feed_name: str,
    *,
    pat: str = "",
) -> None:
    """Export retention policy for a single feed."""
    try:
        data = azcli.invoke(
            "packaging", "retentionpolicies",
            org_url=org_url,
            project=project_name,
            route_parameters={"feedId": feed_id},
            paginate=False,
        )
        out_path = art_dir / f"feed_{feed_name}_retention.json"
        writers.write_json(out_path, redact.redact(data))
        inventory.add("artifacts", f"{project_name}/feeds/{feed_name}/retention", str(out_path))
        logger.info("Exported retention policy for feed '%s'", feed_name)
    except Exception as exc:
        logger.warning("Failed to export retention for feed '%s': %s", feed_name, exc)
        inventory.add_error("artifacts", f"{project_name}/feeds/{feed_name}/retention",
                            str(exc), pat=pat)
