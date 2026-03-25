"""Wiki backup: wiki list and page content export."""

from __future__ import annotations

import logging
from typing import Any

import azcli
import redact
import writers
from inventory import Inventory
from paths import BackupPaths, safe_name

logger = logging.getLogger(__name__)


def backup_wikis(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    pat: str = "",
    dry_run: bool = False,
    max_items: int = 0,
) -> None:
    """Back up wikis and their page content for a project."""
    logger.info("Backing up wikis for project '%s' …", project_name)

    if dry_run:
        logger.info("[DRY-RUN] Would export wikis for %s", project_name)
        return

    wiki_dir = paths.wikis_dir(project_name)

    try:
        data = azcli.invoke(
            "wiki", "wikis",
            org_url=org_url,
            project=project_name,
        )
        wikis = data.get("value", data) if isinstance(data, dict) else data
        if not isinstance(wikis, list):
            wikis = [wikis] if wikis else []

        writers.write_json(wiki_dir / "wikis.json", redact.redact(wikis))
        inventory.add("wikis", f"{project_name}/wikis", str(wiki_dir / "wikis.json"), len(wikis))
        logger.info("Exported %d wiki(s) for '%s'", len(wikis), project_name)

        for wiki in wikis:
            wiki_id = wiki.get("id", "")
            wiki_name = safe_name(wiki.get("name", "unknown"))
            if not wiki_id:
                continue
            _export_wiki_pages(wiki_dir, inventory, org_url, project_name,
                               wiki_id, wiki_name, pat=pat)

    except Exception as exc:
        logger.warning("Failed to export wikis for '%s': %s", project_name, exc)
        inventory.add_error("wikis", f"{project_name}/wikis", str(exc), pat=pat)


def _export_wiki_pages(
    wiki_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    wiki_id: str,
    wiki_name: str,
    *,
    pat: str = "",
) -> None:
    """Export the full page tree (with content) for a single wiki."""
    try:
        data = azcli.invoke(
            "wiki", "pages",
            org_url=org_url,
            project=project_name,
            route_parameters={"wikiIdentifier": wiki_id},
            query_parameters={"path": "/", "recursionLevel": "full", "includeContent": "true"},
            paginate=False,
        )
        out_path = wiki_dir / f"wiki_{wiki_name}_pages.json"
        writers.write_json(out_path, redact.redact(data))
        inventory.add("wikis", f"{project_name}/wikis/{wiki_name}/pages", str(out_path))
        logger.info("Exported pages for wiki '%s'", wiki_name)
    except Exception as exc:
        logger.warning("Failed to export pages for wiki '%s': %s", wiki_name, exc)
        inventory.add_error("wikis", f"{project_name}/wikis/{wiki_name}/pages", str(exc), pat=pat)
