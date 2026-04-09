"""Test plans backup: test plans and suites."""

from __future__ import annotations

import logging
from typing import Any

import azcli
import redact
import writers
from inventory import Inventory
from paths import BackupPaths, safe_name

logger = logging.getLogger(__name__)


def backup_testplans(
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
    """Back up test plans and their suites for a project.

    *since* is accepted for API consistency but not currently used — the
    Azure DevOps test plans API does not support date-based filtering.
    """
    logger.info("Backing up test plans for project '%s' …", project_name)

    if dry_run:
        logger.info("[DRY-RUN] Would export test plans for %s", project_name)
        return

    tp_dir = paths.testplans_dir(project_name)

    try:
        qp: dict[str, str] = {}
        if max_items:
            qp["$top"] = str(max_items)
        data = azcli.invoke(
            "test", "plans",
            org_url=org_url,
            project=project_name,
            query_parameters=qp if qp else None,
            timeout=timeout,
        )
        plans = data.get("value", data) if isinstance(data, dict) else data
        if not isinstance(plans, list):
            plans = [plans] if plans else []

        writers.write_json(tp_dir / "plans.json", redact.redact(plans))
        inventory.add("testplans", f"{project_name}/plans",
                       str(tp_dir / "plans.json"), len(plans))
        logger.info("Exported %d test plan(s) for '%s'", len(plans), project_name)

        for plan in plans:
            plan_id = plan.get("id", "")
            plan_name = safe_name(plan.get("name", "unknown"))
            if not plan_id:
                continue
            _export_plan_suites(tp_dir, inventory, org_url, project_name,
                                plan_id, plan_name, pat=pat)

    except Exception as exc:
        logger.warning("Failed to export test plans for '%s': %s", project_name, exc)
        inventory.add_error("testplans", f"{project_name}/plans", str(exc), pat=pat)


def _export_plan_suites(
    tp_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    plan_id: str,
    plan_name: str,
    *,
    pat: str = "",
) -> None:
    """Export test suites for a single test plan."""
    try:
        data = azcli.invoke(
            "test", "suites",
            org_url=org_url,
            project=project_name,
            route_parameters={"planId": str(plan_id)},
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            items = [items] if items else []
        out_path = tp_dir / f"plan_{plan_name}_suites.json"
        writers.write_json(out_path, redact.redact(items))
        inventory.add("testplans", f"{project_name}/plans/{plan_name}/suites",
                       str(out_path), len(items))
        logger.info("Exported %d suite(s) for test plan '%s'", len(items), plan_name)
    except Exception as exc:
        logger.warning("Failed to export suites for test plan '%s': %s", plan_name, exc)
        inventory.add_error("testplans", f"{project_name}/plans/{plan_name}/suites",
                            str(exc), pat=pat)
