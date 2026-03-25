"""Git repository backup: list repos, clone content."""

from __future__ import annotations

import logging
from typing import Any

import azcli
import redact
import writers
from inventory import Inventory
from paths import BackupPaths

logger = logging.getLogger(__name__)


def backup_git(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    *,
    pat: str = "",
    dry_run: bool = False,
    max_items: int = 0,
) -> None:
    """Back up all Git repositories for a project."""
    logger.info("Backing up Git repos for project '%s' …", project_name)

    try:
        repos = azcli.az("repos", "list", org_url=org_url, project=project_name)
    except Exception as exc:
        logger.warning("Failed to list repos for '%s': %s", project_name, exc)
        inventory.add_error("git", f"{project_name}/repos", str(exc), pat=pat)
        return

    if not isinstance(repos, list):
        repos = repos.get("value", []) if isinstance(repos, dict) else []

    # Write repos index
    git_dir = paths.git_dir(project_name)
    writers.write_json(git_dir / "repos.json", redact.redact(repos))
    inventory.add("git", f"{project_name}/repos", str(git_dir / "repos.json"), len(repos))

    for i, repo in enumerate(repos):
        if max_items and i >= max_items:
            logger.info("Reached max_items limit (%d) for repos", max_items)
            break
        repo_name = repo.get("name", "unknown")
        remote_url = repo.get("remoteUrl", "")
        if not remote_url:
            logger.warning("No remoteUrl for repo '%s', skipping clone", repo_name)
            continue
        _clone_repo(paths, inventory, org_url, project_name, repo_name, remote_url, pat, dry_run=dry_run)
        _export_repo_metadata(paths, inventory, org_url, project_name, repo, dry_run=dry_run)


def _clone_repo(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    repo_name: str,
    remote_url: str,
    pat: str,
    *,
    dry_run: bool,
) -> None:
    dest = paths.repo_dir(project_name, repo_name)
    if dry_run:
        logger.info("[DRY-RUN] Would clone %s -> %s", repo_name, dest)
        return
    try:
        azcli.git_clone(remote_url, dest, pat=pat)
        inventory.add("git", f"{project_name}/{repo_name}", str(dest))
        logger.info("Cloned repo '%s'", repo_name)
    except Exception as exc:
        logger.warning("Failed to clone repo '%s': %s", repo_name, exc)
        inventory.add_error("git", f"{project_name}/{repo_name}", str(exc), pat=pat)


def _export_repo_metadata(
    paths: BackupPaths,
    inventory: Inventory,
    org_url: str,
    project_name: str,
    repo: dict[str, Any],
    *,
    dry_run: bool,
) -> None:
    """Export branches, tags, policies, and permissions for a repository."""
    repo_name = repo.get("name", "unknown")
    repo_id = repo.get("id", "")
    project_id = repo.get("project", {}).get("id", "")
    if dry_run:
        return

    # Branches
    try:
        branches = azcli.invoke(
            "git", "refs",
            org_url=org_url,
            project=project_name,
            route_parameters={"repositoryId": repo_id},
            query_parameters={"filter": "heads/"},
        )
        items = branches.get("value", branches) if isinstance(branches, dict) else branches
        dest = paths.repo_dir(project_name, repo_name)
        writers.write_json(dest.parent / f"{repo_name}_branches.json", redact.redact(items))
    except Exception as exc:
        logger.debug("Could not export branches for '%s': %s", repo_name, exc)

    # Tags
    try:
        tags = azcli.invoke(
            "git", "refs",
            org_url=org_url,
            project=project_name,
            route_parameters={"repositoryId": repo_id},
            query_parameters={"filter": "tags/"},
        )
        items = tags.get("value", tags) if isinstance(tags, dict) else tags
        dest = paths.repo_dir(project_name, repo_name)
        writers.write_json(dest.parent / f"{repo_name}_tags.json", redact.redact(items))
    except Exception as exc:
        logger.debug("Could not export tags for '%s': %s", repo_name, exc)

    # Policies (filtered by repository)
    try:
        policies = azcli.invoke(
            "policy", "configurations",
            org_url=org_url,
            project=project_name,
            query_parameters={"repositoryId": repo_id},
        )
        items = policies.get("value", policies) if isinstance(policies, dict) else policies
        dest = paths.repo_dir(project_name, repo_name)
        writers.write_json(dest.parent / f"{repo_name}_policies.json", redact.redact(items))
    except Exception as exc:
        logger.debug("Could not export policies for '%s': %s", repo_name, exc)

    # Permissions (repo-scoped ACL via token filter)
    if project_id and repo_id:
        try:
            token = f"repoV2/{project_id}/{repo_id}"
            data = azcli.invoke(
                "security", "accesscontrollists",
                org_url=org_url,
                project=project_name,
                query_parameters={"token": token},
            )
            items = data.get("value", data) if isinstance(data, dict) else data
            dest = paths.repo_dir(project_name, repo_name)
            writers.write_json(dest.parent / f"{repo_name}_permissions.json", redact.redact(items))
            count = len(items) if isinstance(items, list) else 1
            inventory.add("git", f"{project_name}/{repo_name}/permissions",
                           str(dest.parent / f"{repo_name}_permissions.json"), count)
            logger.debug("Exported permissions for repo '%s'", repo_name)
        except Exception as exc:
            logger.debug("Could not export permissions for '%s': %s", repo_name, exc)
