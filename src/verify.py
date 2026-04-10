"""Post-backup verification: randomly sample backed-up items and compare against the live ADO instance."""

from __future__ import annotations

import datetime
import json
import logging
import random
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import azcli
import writers

logger = logging.getLogger(__name__)

# Sentinel statuses
_PASS = "pass"
_FAIL = "fail"
_SKIP = "skip"
_ERROR = "error"


@dataclass
class VerificationResult:
    category: str
    project: str
    item: str
    status: str          # pass | fail | skip | error
    check: str
    backed_up_value: Any = None
    live_value: Any = None
    note: str = ""


@dataclass
class VerificationReport:
    verified_at: str
    backup_path: str
    org_url: str
    samples_per_category: int
    results: list[VerificationResult] = field(default_factory=list)

    @property
    def summary(self) -> dict[str, int]:
        return {
            "total": len(self.results),
            "passed": sum(1 for r in self.results if r.status == _PASS),
            "failed": sum(1 for r in self.results if r.status == _FAIL),
            "skipped": sum(1 for r in self.results if r.status == _SKIP),
            "errors": sum(1 for r in self.results if r.status == _ERROR),
        }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def verify_backup(
    backup_base: Path,
    org_url: str,
    *,
    pat: str = "",
    samples: int = 3,
) -> VerificationReport:
    """Verify a completed backup by sampling items from each scope against the live ADO instance.

    Parameters
    ----------
    backup_base:
        The timestamped backup directory (contains ``_indexes/`` and ``projects/``).
    org_url:
        Azure DevOps organisation URL.
    pat:
        Personal access token (optional; uses az CLI session if absent).
    samples:
        Number of items to sample per category per project.
    """
    report = VerificationReport(
        verified_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        backup_path=str(backup_base),
        org_url=org_url,
        samples_per_category=samples,
    )

    # Read manifest for backup start time and active components
    manifest_path = backup_base / "_indexes" / "manifest.json"
    backup_started_at: str = ""
    active_components: set[str] = set()
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            backup_started_at = manifest.get("started_at", "")
            active_components = set(manifest.get("limits_applied", {}).get("components", []))
        except Exception as exc:
            logger.warning("Could not read manifest: %s", exc)

    # Discover project directories
    projects_dir = backup_base / "projects"
    project_dirs = [d for d in projects_dir.iterdir() if d.is_dir()] if projects_dir.exists() else []

    for proj_dir in project_dirs:
        project_name = proj_dir.name

        if not active_components or "git" in active_components:
            report.results.extend(
                _verify_git(proj_dir, org_url, project_name, pat, samples, backup_started_at)
            )
        if not active_components or "boards" in active_components:
            report.results.extend(
                _verify_work_items(proj_dir, org_url, project_name, pat, samples, backup_started_at)
            )
        if not active_components or "pipelines" in active_components:
            report.results.extend(
                _verify_pipelines(proj_dir, org_url, project_name, pat, samples, backup_started_at)
            )
        if not active_components or "pull_requests" in active_components:
            report.results.extend(
                _verify_pull_requests(proj_dir, org_url, project_name, pat, samples, backup_started_at)
            )
        if not active_components or "wikis" in active_components:
            report.results.extend(
                _verify_wikis(proj_dir, org_url, project_name, pat, samples, backup_started_at)
            )
        if not active_components or "artifacts" in active_components:
            report.results.extend(
                _verify_artifacts(proj_dir, org_url, project_name, pat, samples, backup_started_at)
            )
        if not active_components or "dashboards" in active_components:
            report.results.extend(
                _verify_dashboards(proj_dir, org_url, project_name, pat, samples, backup_started_at)
            )
        if not active_components or "testplans" in active_components:
            report.results.extend(
                _verify_testplans(proj_dir, org_url, project_name, pat, samples, backup_started_at)
            )

    _write_report(report, backup_base / "_indexes" / "verification_report.json")

    s = report.summary
    logger.info(
        "Verification complete: %d passed, %d failed, %d skipped, %d errors",
        s["passed"], s["failed"], s["skipped"], s["errors"],
    )
    return report


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def _write_report(report: VerificationReport, path: Path) -> None:
    data = {
        "verified_at": report.verified_at,
        "backup_path": report.backup_path,
        "org_url": report.org_url,
        "samples_per_category": report.samples_per_category,
        "summary": report.summary,
        "results": [
            {
                "category": r.category,
                "project": r.project,
                "item": r.item,
                "status": r.status,
                "check": r.check,
                "backed_up_value": r.backed_up_value,
                "live_value": r.live_value,
                "note": r.note,
            }
            for r in report.results
        ],
    }
    writers.write_json(path, data)
    logger.info("Verification report written to %s", path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sample(items: list[Any], n: int) -> list[Any]:
    if len(items) <= n:
        return list(items)
    return random.sample(items, n)


def _is_fresh(item_modified: str, backup_started_at: str) -> bool:
    """Return True if the item was modified after the backup started (skip it)."""
    if not item_modified or not backup_started_at:
        return False
    try:
        mod = datetime.datetime.fromisoformat(item_modified.replace("Z", "+00:00"))
        started = datetime.datetime.fromisoformat(backup_started_at.replace("Z", "+00:00"))
        return mod > started
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Per-category verifiers
# ---------------------------------------------------------------------------

def _verify_git(
    proj_dir: Path, org_url: str, project: str, pat: str, n: int, backup_started_at: str
) -> list[VerificationResult]:
    results: list[VerificationResult] = []
    repos_file = proj_dir / "git" / "repos.json"
    if not repos_file.exists():
        return results

    try:
        repos = _load_json(repos_file)
    except Exception as exc:
        logger.debug("Could not load repos.json for %s: %s", project, exc)
        return results

    if not isinstance(repos, list):
        return results

    for repo in _sample(repos, n):
        repo_name = repo.get("name", "unknown")
        repo_id = repo.get("id", "")
        default_branch = repo.get("defaultBranch", "refs/heads/main")
        # Normalise: "refs/heads/main" → "main"
        branch_short = default_branch.replace("refs/heads/", "") if default_branch else "main"

        bare_dir = proj_dir / "git" / repo_name
        item_label = f"git/{repo_name}"

        # Skip if clone was compressed
        if not bare_dir.exists():
            results.append(VerificationResult(
                category="git", project=project, item=item_label,
                status=_SKIP, check="bare_clone_exists",
                note="Bare clone directory not found (may be compressed)",
            ))
            continue

        # Get HEAD SHA from local bare clone
        try:
            proc = subprocess.run(
                ["git", "-C", str(bare_dir), "rev-parse", f"refs/heads/{branch_short}"],
                capture_output=True, text=True, timeout=30,
            )
            local_sha = proc.stdout.strip() if proc.returncode == 0 else ""
        except Exception as exc:
            results.append(VerificationResult(
                category="git", project=project, item=item_label,
                status=_ERROR, check="local_head_sha",
                note=f"git rev-parse failed: {exc}",
            ))
            continue

        if not local_sha:
            results.append(VerificationResult(
                category="git", project=project, item=item_label,
                status=_SKIP, check="local_head_sha",
                note=f"Could not resolve refs/heads/{branch_short} in bare clone",
            ))
            continue

        # Get latest commit SHA from live API
        try:
            data = azcli.invoke(
                "git", "refs",
                org_url=org_url, project=project,
                route_parameters={"repositoryId": repo_id},
                query_parameters={"filter": f"heads/{branch_short}"},
                paginate=False,
            )
            refs = data.get("value", []) if isinstance(data, dict) else []
            live_sha = refs[0].get("objectId", "") if refs else ""
        except Exception as exc:
            results.append(VerificationResult(
                category="git", project=project, item=item_label,
                status=_ERROR, check="live_head_sha",
                note=f"API call failed: {exc}",
            ))
            continue

        if not live_sha:
            results.append(VerificationResult(
                category="git", project=project, item=item_label,
                status=_SKIP, check="live_head_sha",
                note="Could not retrieve live branch SHA",
            ))
            continue

        status = _PASS if local_sha == live_sha else _FAIL
        note = "HEAD SHA matches" if status == _PASS else "HEAD SHA differs - repo may have new commits since backup"
        results.append(VerificationResult(
            category="git", project=project, item=item_label,
            status=status, check="head_sha_match",
            backed_up_value=local_sha, live_value=live_sha, note=note,
        ))

    return results


def _verify_work_items(
    proj_dir: Path, org_url: str, project: str, pat: str, n: int, backup_started_at: str
) -> list[VerificationResult]:
    results: list[VerificationResult] = []
    index_file = proj_dir / "boards" / "work_items" / "index.json"
    if not index_file.exists():
        return results

    try:
        index = _load_json(index_file)
        ids = index.get("ids", []) if isinstance(index, dict) else []
    except Exception as exc:
        logger.debug("Could not load work_items/index.json for %s: %s", project, exc)
        return results

    wi_dir = proj_dir / "boards" / "work_items"
    for wi_id in _sample(ids, n):
        item_label = f"work_item/{wi_id}"
        wi_file = wi_dir / f"{wi_id}.json"

        if not wi_file.exists():
            results.append(VerificationResult(
                category="boards", project=project, item=item_label,
                status=_SKIP, check="backup_file_exists",
                note="Work item file not found in backup",
            ))
            continue

        try:
            backed_up = _load_json(wi_file)
        except Exception as exc:
            results.append(VerificationResult(
                category="boards", project=project, item=item_label,
                status=_ERROR, check="read_backup_file",
                note=f"Could not read backup file: {exc}",
            ))
            continue

        fields = backed_up.get("fields", {})
        backed_rev = fields.get("System.Rev") or backed_up.get("rev")
        changed_date = fields.get("System.ChangedDate", "")

        # Skip if item was modified after backup started
        if _is_fresh(changed_date, backup_started_at):
            results.append(VerificationResult(
                category="boards", project=project, item=item_label,
                status=_SKIP, check="work_item_revision",
                note=f"Item modified ({changed_date}) after backup started ({backup_started_at})",
            ))
            continue

        # Re-fetch from API
        try:
            live = azcli.invoke(
                "wit", "workItems",
                route_parameters={"id": str(wi_id)},
                query_parameters={"$expand": "all"},
                org_url=org_url, project=project,
                paginate=False,
            )
            live_fields = live.get("fields", {}) if isinstance(live, dict) else {}
            live_rev = live_fields.get("System.Rev") or (live.get("rev") if isinstance(live, dict) else None)
        except Exception as exc:
            results.append(VerificationResult(
                category="boards", project=project, item=item_label,
                status=_ERROR, check="work_item_revision",
                note=f"API call failed: {exc}",
            ))
            continue

        status = _PASS if backed_rev == live_rev else _FAIL
        note = "System.Rev matches" if status == _PASS else "System.Rev differs - work item was updated after backup"
        results.append(VerificationResult(
            category="boards", project=project, item=item_label,
            status=status, check="work_item_revision",
            backed_up_value=backed_rev, live_value=live_rev, note=note,
        ))

    return results


def _verify_pipelines(
    proj_dir: Path, org_url: str, project: str, pat: str, n: int, backup_started_at: str
) -> list[VerificationResult]:
    results: list[VerificationResult] = []
    pipelines_file = proj_dir / "pipelines" / "pipelines.json"
    if not pipelines_file.exists():
        return results

    try:
        pipelines = _load_json(pipelines_file)
    except Exception as exc:
        logger.debug("Could not load pipelines.json for %s: %s", project, exc)
        return results

    if not isinstance(pipelines, list):
        return results

    for pipeline in _sample(pipelines, n):
        pipeline_id = pipeline.get("id")
        pipeline_name = pipeline.get("name", str(pipeline_id))
        item_label = f"pipeline/{pipeline_id}"
        backed_rev = pipeline.get("revision")

        try:
            live = azcli.invoke(
                "build", "definitions",
                route_parameters={"definitionId": str(pipeline_id)},
                org_url=org_url, project=project,
                paginate=False,
            )
            live_rev = live.get("revision") if isinstance(live, dict) else None
        except Exception as exc:
            results.append(VerificationResult(
                category="pipelines", project=project, item=item_label,
                status=_ERROR, check="pipeline_revision",
                note=f"API call failed: {exc}",
            ))
            continue

        if backed_rev is None or live_rev is None:
            results.append(VerificationResult(
                category="pipelines", project=project, item=item_label,
                status=_SKIP, check="pipeline_revision",
                note="Revision field not present in backed-up or live data",
            ))
            continue

        status = _PASS if backed_rev == live_rev else _FAIL
        note = "revision matches" if status == _PASS else "revision differs - pipeline was updated after backup"
        results.append(VerificationResult(
            category="pipelines", project=project, item=item_label,
            status=status, check="pipeline_revision",
            backed_up_value=backed_rev, live_value=live_rev, note=note,
        ))

    return results


def _verify_pull_requests(
    proj_dir: Path, org_url: str, project: str, pat: str, n: int, backup_started_at: str
) -> list[VerificationResult]:
    results: list[VerificationResult] = []
    pr_base = proj_dir / "pull_requests"
    if not pr_base.exists():
        return results

    # Collect PRs across all repo subdirectories
    all_prs: list[tuple[str, dict]] = []  # (repo_id, pr_dict)
    for repo_dir in pr_base.iterdir():
        if not repo_dir.is_dir():
            continue
        pr_file = repo_dir / "pull_requests.json"
        if not pr_file.exists():
            continue
        try:
            prs = _load_json(pr_file)
            if not isinstance(prs, list):
                prs = prs.get("value", []) if isinstance(prs, dict) else []
            for pr in prs:
                repo_id = pr.get("repository", {}).get("id", "")
                if repo_id:
                    all_prs.append((repo_id, pr))
        except Exception as exc:
            logger.debug("Could not load pull_requests.json in %s: %s", repo_dir, exc)

    for repo_id, pr in _sample(all_prs, n):
        pr_id = pr.get("pullRequestId")
        item_label = f"pull_request/{pr_id}"
        backed_status = pr.get("status")
        closed_date = pr.get("closedDate", "")

        if _is_fresh(closed_date, backup_started_at):
            results.append(VerificationResult(
                category="pull_requests", project=project, item=item_label,
                status=_SKIP, check="pr_status",
                note=f"PR closed/updated ({closed_date}) after backup started",
            ))
            continue

        try:
            live = azcli.invoke(
                "git", "pullRequests",
                route_parameters={"repositoryId": repo_id, "pullRequestId": str(pr_id)},
                org_url=org_url, project=project,
                paginate=False,
            )
            live_status = live.get("status") if isinstance(live, dict) else None
        except Exception as exc:
            results.append(VerificationResult(
                category="pull_requests", project=project, item=item_label,
                status=_ERROR, check="pr_status",
                note=f"API call failed: {exc}",
            ))
            continue

        status = _PASS if backed_status == live_status else _FAIL
        note = "status matches" if status == _PASS else f"status differs: backed up={backed_status!r}, live={live_status!r}"
        results.append(VerificationResult(
            category="pull_requests", project=project, item=item_label,
            status=status, check="pr_status",
            backed_up_value=backed_status, live_value=live_status, note=note,
        ))

    return results


def _verify_wikis(
    proj_dir: Path, org_url: str, project: str, pat: str, n: int, backup_started_at: str
) -> list[VerificationResult]:
    results: list[VerificationResult] = []
    wikis_dir = proj_dir / "wikis"
    if not wikis_dir.exists():
        return results

    wikis_file = wikis_dir / "wikis.json"
    if not wikis_file.exists():
        return results

    try:
        wikis = _load_json(wikis_file)
        if not isinstance(wikis, list):
            wikis = wikis.get("value", []) if isinstance(wikis, dict) else []
    except Exception as exc:
        logger.debug("Could not load wikis.json for %s: %s", project, exc)
        return results

    for wiki in _sample(wikis, n):
        wiki_name = wiki.get("name", wiki.get("id", "unknown"))
        safe_name = wiki_name.replace("/", "_").replace(" ", "_")
        item_label = f"wiki/{wiki_name}"
        pages_file = wikis_dir / f"wiki_{safe_name}_pages.json"

        if not pages_file.exists():
            results.append(VerificationResult(
                category="wikis", project=project, item=item_label,
                status=_SKIP, check="pages_file_exists",
                note="Pages file not found in backup",
            ))
            continue

        size = pages_file.stat().st_size
        status = _PASS if size > 2 else _FAIL
        note = f"Pages file present ({size} bytes)" if status == _PASS else "Pages file is empty"
        results.append(VerificationResult(
            category="wikis", project=project, item=item_label,
            status=status, check="pages_file_non_empty",
            backed_up_value=size, note=note,
        ))

    return results


def _verify_artifacts(
    proj_dir: Path, org_url: str, project: str, pat: str, n: int, backup_started_at: str
) -> list[VerificationResult]:
    results: list[VerificationResult] = []
    artifacts_dir = proj_dir / "artifacts"
    if not artifacts_dir.exists():
        return results

    feeds_file = artifacts_dir / "feeds.json"
    if not feeds_file.exists():
        return results

    try:
        feeds = _load_json(feeds_file)
        if not isinstance(feeds, list):
            feeds = feeds.get("value", []) if isinstance(feeds, dict) else []
    except Exception as exc:
        logger.debug("Could not load feeds.json for %s: %s", project, exc)
        return results

    for feed in _sample(feeds, n):
        feed_id = feed.get("id", "")
        feed_name = feed.get("name", feed_id)
        safe_fname = feed_name.replace("/", "_").replace(" ", "_")
        item_label = f"feed/{feed_name}"
        pkg_file = artifacts_dir / f"feed_{safe_fname}_packages.json"

        if not pkg_file.exists():
            results.append(VerificationResult(
                category="artifacts", project=project, item=item_label,
                status=_SKIP, check="packages_count",
                note="Packages file not found in backup",
            ))
            continue

        try:
            backed_pkgs = _load_json(pkg_file)
            backed_count = len(backed_pkgs) if isinstance(backed_pkgs, list) else (
                backed_pkgs.get("count", len(backed_pkgs.get("value", []))) if isinstance(backed_pkgs, dict) else 0
            )
        except Exception as exc:
            results.append(VerificationResult(
                category="artifacts", project=project, item=item_label,
                status=_ERROR, check="packages_count",
                note=f"Could not read packages file: {exc}",
            ))
            continue

        try:
            live_data = azcli.invoke(
                "packaging", "packages",
                route_parameters={"feedId": feed_id},
                query_parameters={"$top": "1"},
                org_url=org_url, project=project,
                paginate=False,
            )
            live_count = live_data.get("count", None) if isinstance(live_data, dict) else None
        except Exception as exc:
            results.append(VerificationResult(
                category="artifacts", project=project, item=item_label,
                status=_ERROR, check="packages_count",
                note=f"API call failed: {exc}",
            ))
            continue

        if live_count is None:
            results.append(VerificationResult(
                category="artifacts", project=project, item=item_label,
                status=_SKIP, check="packages_count",
                note="Live package count not available from API",
            ))
            continue

        status = _PASS if backed_count == live_count else _FAIL
        note = "package count matches" if status == _PASS else f"package count differs - packages may have been added/removed since backup"
        results.append(VerificationResult(
            category="artifacts", project=project, item=item_label,
            status=status, check="packages_count",
            backed_up_value=backed_count, live_value=live_count, note=note,
        ))

    return results


def _verify_dashboards(
    proj_dir: Path, org_url: str, project: str, pat: str, n: int, backup_started_at: str
) -> list[VerificationResult]:
    results: list[VerificationResult] = []
    dash_dir = proj_dir / "dashboards"
    if not dash_dir.exists():
        return results

    dash_file = dash_dir / "dashboards.json"
    if not dash_file.exists():
        return results

    try:
        dashboards = _load_json(dash_file)
        if not isinstance(dashboards, list):
            dashboards = dashboards.get("value", []) if isinstance(dashboards, dict) else []
    except Exception as exc:
        logger.debug("Could not load dashboards.json for %s: %s", project, exc)
        return results

    for dashboard in _sample(dashboards, n):
        dash_id = dashboard.get("id", "")
        dash_name = dashboard.get("name", dash_id)
        item_label = f"dashboard/{dash_name}"

        if not dash_id:
            results.append(VerificationResult(
                category="dashboards", project=project, item=item_label,
                status=_SKIP, check="dashboard_exists",
                note="Dashboard has no id field",
            ))
            continue

        try:
            live = azcli.invoke(
                "dashboard", "dashboards",
                org_url=org_url, project=project,
                paginate=False,
            )
            live_dashboards = live.get("value", live) if isinstance(live, dict) else live
            if not isinstance(live_dashboards, list):
                live_dashboards = [live_dashboards] if live_dashboards else []
            live_ids = {d.get("id") for d in live_dashboards}
        except Exception as exc:
            results.append(VerificationResult(
                category="dashboards", project=project, item=item_label,
                status=_ERROR, check="dashboard_exists",
                note=f"API call failed: {exc}",
            ))
            continue

        status = _PASS if dash_id in live_ids else _FAIL
        note = "Dashboard exists in live instance" if status == _PASS else "Dashboard not found in live instance"
        results.append(VerificationResult(
            category="dashboards", project=project, item=item_label,
            status=status, check="dashboard_exists",
            backed_up_value=dash_id, live_value=list(live_ids), note=note,
        ))

    return results


def _verify_testplans(
    proj_dir: Path, org_url: str, project: str, pat: str, n: int, backup_started_at: str
) -> list[VerificationResult]:
    results: list[VerificationResult] = []
    tp_dir = proj_dir / "test_plans"
    if not tp_dir.exists():
        return results

    plans_file = tp_dir / "plans.json"
    if not plans_file.exists():
        return results

    try:
        plans = _load_json(plans_file)
        if not isinstance(plans, list):
            plans = plans.get("value", []) if isinstance(plans, dict) else []
    except Exception as exc:
        logger.debug("Could not load plans.json for %s: %s", project, exc)
        return results

    for plan in _sample(plans, n):
        plan_id = plan.get("id", "")
        plan_name = plan.get("name", str(plan_id))
        item_label = f"testplan/{plan_name}"

        if not plan_id:
            results.append(VerificationResult(
                category="testplans", project=project, item=item_label,
                status=_SKIP, check="testplan_exists",
                note="Test plan has no id field",
            ))
            continue

        try:
            live = azcli.invoke(
                "test", "plans",
                org_url=org_url, project=project,
                paginate=False,
            )
            live_plans = live.get("value", live) if isinstance(live, dict) else live
            if not isinstance(live_plans, list):
                live_plans = [live_plans] if live_plans else []
            live_ids = {p.get("id") for p in live_plans}
        except Exception as exc:
            results.append(VerificationResult(
                category="testplans", project=project, item=item_label,
                status=_ERROR, check="testplan_exists",
                note=f"API call failed: {exc}",
            ))
            continue

        status = _PASS if plan_id in live_ids else _FAIL
        note = "Test plan exists in live instance" if status == _PASS else "Test plan not found in live instance"
        results.append(VerificationResult(
            category="testplans", project=project, item=item_label,
            status=status, check="testplan_exists",
            backed_up_value=plan_id, live_value=list(live_ids), note=note,
        ))

    return results
