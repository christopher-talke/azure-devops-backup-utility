"""Dashboards and notification subscriptions backup."""

from __future__ import annotations

import logging
from typing import Any

import azcli
import redact
import writers
from inventory import Inventory
from paths import BackupPaths

logger = logging.getLogger(__name__)


def backup_dashboards(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    pat: str = "",
    dry_run: bool = False,
    timeout: int = 120,
) -> None:
    """Back up dashboards, widgets, and notification subscriptions."""
    logger.info("Backing up dashboards and notifications for project '%s' …", project_name)

    if dry_run:
        logger.info("[DRY-RUN] Would export dashboards for %s", project_name)
        return

    dash_dir = paths.dashboards_dir(project_name)

    _export_dashboards(dash_dir, inventory, org_url, project_name, pat=pat, timeout=timeout)
    _export_notifications(dash_dir, inventory, org_url, project_name, pat=pat, timeout=timeout)


def _export_dashboards(
    dash_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    pat: str = "",
    timeout: int = 120,
) -> None:
    """Export dashboards and their widget configurations."""
    try:
        data = azcli.invoke(
            "dashboard", "dashboards",
            org_url=org_url,
            project=project_name,
            timeout=timeout,
        )
        dashboards = data.get("value", data) if isinstance(data, dict) else data
        if not isinstance(dashboards, list):
            dashboards = [dashboards] if dashboards else []

        # Export dashboard list
        writers.write_json(dash_dir / "dashboards.json", redact.redact(dashboards))
        inventory.add("dashboards", f"{project_name}/dashboards",
                       str(dash_dir / "dashboards.json"), len(dashboards))
        logger.info("Exported %d dashboard(s) for '%s'", len(dashboards), project_name)

        # Export widgets per dashboard
        for dashboard in dashboards:
            dash_id = dashboard.get("id", "")
            dash_name = dashboard.get("name", "unknown")
            if not dash_id:
                continue
            try:
                widget_data = azcli.invoke(
                    "dashboard", "widgets",
                    org_url=org_url,
                    project=project_name,
                    route_parameters={"dashboardId": dash_id},
                    paginate=False,
                )
                widgets = widget_data.get("value", widget_data) if isinstance(widget_data, dict) else widget_data
                out_path = dash_dir / f"dashboard_{dash_name}_widgets.json"
                writers.write_json(out_path, redact.redact(widgets))
            except Exception as exc:
                logger.debug("Could not export widgets for dashboard '%s': %s", dash_name, exc)

    except Exception as exc:
        logger.warning("Failed to export dashboards for '%s': %s", project_name, exc)
        inventory.add_error("dashboards", f"{project_name}/dashboards", str(exc), pat=pat)


def _export_notifications(
    dash_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    pat: str = "",
    timeout: int = 120,
) -> None:
    """Export notification subscriptions for the project."""
    try:
        data = azcli.invoke(
            "notification", "subscriptions",
            org_url=org_url,
            project=project_name,
            timeout=timeout,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        out_path = dash_dir / "notification_subscriptions.json"
        writers.write_json(out_path, redact.redact(items))
        count = len(items) if isinstance(items, list) else 1
        inventory.add("dashboards", f"{project_name}/notification_subscriptions",
                       str(out_path), count)
        logger.info("Exported notification subscriptions for '%s'", project_name)
    except Exception as exc:
        logger.warning("Failed to export notification subscriptions for '%s': %s", project_name, exc)
        inventory.add_error("dashboards", f"{project_name}/notification_subscriptions",
                            str(exc), pat=pat)
