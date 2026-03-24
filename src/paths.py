"""Output path helpers for the backup directory tree."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse


def safe_name(name: str) -> str:
    """Sanitise a name for safe use as a directory or file component.

    Strips leading/trailing dots to prevent ``..`` path traversal and
    replaces any remaining unsafe characters with underscores.
    """
    cleaned = re.sub(r"[^\w\-.]", "_", name).strip(".")
    return cleaned or "_"


def parse_org_url(org_url: str) -> tuple[str, str]:
    """Return ``(host, org_name)`` from an Azure DevOps organisation URL.

    Supports both ``https://dev.azure.com/{org}`` and legacy
    ``https://{org}.visualstudio.com`` forms.
    """
    parsed = urlparse(org_url.rstrip("/"))
    host = parsed.hostname or "unknown"
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if parts:
        org_name = parts[0]
    else:
        # Legacy form: org is the subdomain
        org_name = host.split(".")[0]
    return safe_name(host), safe_name(org_name)


class BackupPaths:
    """Centralised path builder for the backup directory tree."""

    def __init__(self, root: Path, org_url: str, timestamp: str) -> None:
        host, org = parse_org_url(org_url)
        self.base = root / host / org / timestamp
        self.org_dir = self.base / "org"
        self.projects_dir = self.base / "projects"
        self.indexes_dir = self.base / "_indexes"

    # -- organisation scope ---------------------------------------------------
    def org_file(self, name: str) -> Path:
        return self.org_dir / name

    # -- project scope --------------------------------------------------------
    def project_dir(self, project: str) -> Path:
        return self.projects_dir / safe_name(project)

    def metadata_dir(self, project: str) -> Path:
        return self.project_dir(project) / "metadata"

    def git_dir(self, project: str) -> Path:
        return self.project_dir(project) / "git"

    def repo_dir(self, project: str, repo: str) -> Path:
        return self.git_dir(project) / safe_name(repo)

    def boards_dir(self, project: str) -> Path:
        return self.project_dir(project) / "boards"

    def work_items_dir(self, project: str) -> Path:
        return self.boards_dir(project) / "work_items"

    def work_item_attachments_dir(self, project: str, work_item_id: int) -> Path:
        return self.work_items_dir(project) / str(work_item_id) / "attachments"

    def pipelines_dir(self, project: str) -> Path:
        return self.project_dir(project) / "pipelines"

    def pull_requests_dir(self, project: str) -> Path:
        return self.project_dir(project) / "pull_requests"

    def artifacts_dir(self, project: str) -> Path:
        return self.project_dir(project) / "artifacts"

    def dashboards_dir(self, project: str) -> Path:
        return self.project_dir(project) / "dashboards"

    # -- indexes --------------------------------------------------------------
    def inventory_file(self) -> Path:
        return self.indexes_dir / "inventory.json"

    def manifest_file(self) -> Path:
        return self.indexes_dir / "manifest.json"

    def errors_file(self) -> Path:
        return self.indexes_dir / "errors.jsonl"
