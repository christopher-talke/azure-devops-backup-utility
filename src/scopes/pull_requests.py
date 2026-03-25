"""Pull request backup: PR metadata, threads, reviewers, work items, labels, iterations."""

from __future__ import annotations

import logging
from typing import Any

import azcli
import redact
import writers
from inventory import Inventory
from paths import BackupPaths

logger = logging.getLogger(__name__)


def backup_pull_requests(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    pat: str = "",
    dry_run: bool = False,
    max_items: int = 0,
    since: str = "",
) -> None:
    """Back up pull requests (all statuses) and their threads/reviewers."""
    logger.info("Backing up pull requests for project '%s' …", project_name)

    if dry_run:
        logger.info("[DRY-RUN] Would export pull requests for %s", project_name)
        return

    pr_dir = paths.pull_requests_dir(project_name)

    # List all repos to iterate PRs per-repo
    try:
        repos = azcli.az("repos", "list", org_url=org_url, project=project_name)
    except Exception as exc:
        logger.warning("Failed to list repos for PR backup in '%s': %s", project_name, exc)
        inventory.add_error("pull_requests", f"{project_name}/repos", str(exc), pat=pat)
        return

    if not isinstance(repos, list):
        repos = repos.get("value", []) if isinstance(repos, dict) else []

    for repo in repos:
        repo_name = repo.get("name", "unknown")
        repo_id = repo.get("id", "")
        if not repo_id:
            continue
        _export_repo_prs(pr_dir, inventory, org_url, project_name, repo_name, repo_id,
                         pat=pat, max_items=max_items, since=since)


def _export_repo_prs(
    pr_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    repo_name: str,
    repo_id: str,
    *,
    pat: str = "",
    max_items: int = 0,
    since: str = "",
) -> None:
    """Export all PRs for a single repository."""
    try:
        qp: dict[str, str] = {"searchCriteria.status": "all"}
        if max_items:
            qp["$top"] = str(max_items)
        data = azcli.invoke(
            "git", "pullRequests",
            org_url=org_url,
            project=project_name,
            route_parameters={"repositoryId": repo_id},
            query_parameters=qp,
        )
        prs = data.get("value", data) if isinstance(data, dict) else data
        if not isinstance(prs, list):
            prs = [prs] if prs else []

        # Filter by since date if provided
        if since and prs:
            prs = [pr for pr in prs
                   if pr.get("creationDate", "") >= since or pr.get("closedDate", "") >= since]

        repo_pr_dir = pr_dir / repo_name
        writers.write_json(repo_pr_dir / "pull_requests.json", redact.redact(prs))
        inventory.add("pull_requests", f"{project_name}/{repo_name}/pull_requests",
                       str(repo_pr_dir / "pull_requests.json"), len(prs))
        logger.info("Exported %d PRs for '%s/%s'", len(prs), project_name, repo_name)

        # Export threads, work item links, labels, and iterations for each PR
        for pr in prs:
            pr_id = pr.get("pullRequestId")
            if not pr_id:
                continue
            _export_pr_threads(repo_pr_dir, inventory, org_url, project_name,
                               repo_name, repo_id, pr_id, pat=pat)
            _export_pr_work_items(repo_pr_dir, inventory, org_url, project_name,
                                  repo_name, repo_id, pr_id, pat=pat)
            _export_pr_labels(repo_pr_dir, inventory, org_url, project_name,
                              repo_name, repo_id, pr_id, pat=pat)
            _export_pr_iterations(repo_pr_dir, inventory, org_url, project_name,
                                  repo_name, repo_id, pr_id, pat=pat)

    except Exception as exc:
        logger.warning("Failed to export PRs for '%s/%s': %s", project_name, repo_name, exc)
        inventory.add_error("pull_requests", f"{project_name}/{repo_name}/pull_requests",
                            str(exc), pat=pat)


def _export_pr_threads(
    repo_pr_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    repo_name: str,
    repo_id: str,
    pr_id: int,
    *,
    pat: str = "",
) -> None:
    """Export comment threads for a single PR."""
    try:
        data = azcli.invoke(
            "git", "threads",
            org_url=org_url,
            project=project_name,
            route_parameters={"repositoryId": repo_id, "pullRequestId": str(pr_id)},
            paginate=False,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        out_path = repo_pr_dir / str(pr_id) / "threads.json"
        writers.write_json(out_path, redact.redact(items))
    except Exception as exc:
        logger.debug("Could not export threads for PR %d in '%s/%s': %s",
                      pr_id, project_name, repo_name, exc)


def _export_pr_work_items(
    repo_pr_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    repo_name: str,
    repo_id: str,
    pr_id: int,
    *,
    pat: str = "",
) -> None:
    """Export work item links for a single PR."""
    try:
        data = azcli.invoke(
            "git", "pullRequestWorkItems",
            org_url=org_url,
            project=project_name,
            route_parameters={"repositoryId": repo_id, "pullRequestId": str(pr_id)},
            paginate=False,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        out_path = repo_pr_dir / str(pr_id) / "work_items.json"
        writers.write_json(out_path, redact.redact(items))
    except Exception as exc:
        logger.debug("Could not export work items for PR %d in '%s/%s': %s",
                      pr_id, project_name, repo_name, exc)


def _export_pr_labels(
    repo_pr_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    repo_name: str,
    repo_id: str,
    pr_id: int,
    *,
    pat: str = "",
) -> None:
    """Export labels for a single PR."""
    try:
        data = azcli.invoke(
            "git", "pullRequestLabels",
            org_url=org_url,
            project=project_name,
            route_parameters={"repositoryId": repo_id, "pullRequestId": str(pr_id)},
            paginate=False,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        out_path = repo_pr_dir / str(pr_id) / "labels.json"
        writers.write_json(out_path, redact.redact(items))
    except Exception as exc:
        logger.debug("Could not export labels for PR %d in '%s/%s': %s",
                      pr_id, project_name, repo_name, exc)


def _export_pr_iterations(
    repo_pr_dir: Any,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    repo_name: str,
    repo_id: str,
    pr_id: int,
    *,
    pat: str = "",
) -> None:
    """Export iteration (commit) history for a single PR."""
    try:
        data = azcli.invoke(
            "git", "pullRequestIterations",
            org_url=org_url,
            project=project_name,
            route_parameters={"repositoryId": repo_id, "pullRequestId": str(pr_id)},
            paginate=False,
        )
        items = data.get("value", data) if isinstance(data, dict) else data
        out_path = repo_pr_dir / str(pr_id) / "iterations.json"
        writers.write_json(out_path, redact.redact(items))
    except Exception as exc:
        logger.debug("Could not export iterations for PR %d in '%s/%s': %s",
                      pr_id, project_name, repo_name, exc)
