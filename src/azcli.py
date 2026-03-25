"""Thin wrapper around az CLI and az devops invoke calls."""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from backoff import retry

logger = logging.getLogger(__name__)


class AzCliError(Exception):
    """Raised when an az CLI command fails."""

    def __init__(self, message: str, returncode: int = 1, stderr: str = "") -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


class AzCliThrottled(AzCliError):
    """Raised when the server returns HTTP 429 or a 5xx error."""


def _mask_pat(cmd: list[str]) -> list[str]:
    """Return a copy of *cmd* with PAT values masked for logging."""
    masked: list[str] = []
    skip_next = False
    for part in cmd:
        if skip_next:
            masked.append("***")
            skip_next = False
            continue
        if part in ("--pat",):
            masked.append(part)
            skip_next = True
        else:
            masked.append(part)
    return masked


def ensure_devops_extension() -> None:
    """Install the azure-devops extension if it is not already present."""
    try:
        result = subprocess.run(
            ["az", "extension", "show", "-n", "azure-devops"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            logger.debug("azure-devops extension already installed")
            return
    except FileNotFoundError:
        raise AzCliError("Azure CLI (az) is not installed or not on PATH")

    logger.info("Installing azure-devops extension …")
    subprocess.run(
        ["az", "extension", "add", "-n", "azure-devops", "-y"],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )


def configure_defaults(org_url: str, project: str | None = None) -> None:
    """Set az devops defaults for organisation and optionally project.

    NOTE: This writes to ~/.azure/config and persists after the process exits.
    On ephemeral CI/CD runners this is harmless. On shared or long-lived machines,
    run ``az devops configure --defaults organization= project=`` afterwards to clear.
    """
    subprocess.run(
        ["az", "devops", "configure", "--defaults", f"organization={org_url}"],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    if project:
        subprocess.run(
            ["az", "devops", "configure", "--defaults", f"project={project}"],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )


def _run_az(
    cmd: list[str],
    *,
    timeout: int = 120,
    parse_json: bool = True,
) -> Any:
    """Execute an az CLI command and return parsed JSON or raw stdout."""
    log_cmd = _mask_pat(cmd)
    logger.debug("Running: %s", " ".join(log_cmd))

    env = os.environ.copy()

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        # Detect throttling
        if "429" in stderr or "TooManyRequests" in stderr:
            raise AzCliThrottled(f"Throttled: {stderr}", result.returncode, stderr)
        if re.search(r"\b5\d{2}\b", stderr):
            raise AzCliThrottled(f"Server error: {stderr}", result.returncode, stderr)
        raise AzCliError(
            f"az command failed (rc={result.returncode}): {stderr}",
            result.returncode,
            stderr,
        )

    stdout = result.stdout.strip()
    if not stdout:
        return None if parse_json else ""

    if parse_json:
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            logger.warning("Could not parse JSON from az output, returning raw string")
            return stdout
    return stdout


def az(
    *parts: str,
    timeout: int = 120,
    parse_json: bool = True,
    org_url: str = "",
    project: str = "",
    max_retries: int = 3,
) -> Any:
    """Run an arbitrary ``az`` command with retry support.

    Parameters
    ----------
    parts:
        Command parts, e.g. ``"devops", "project", "list"``.
    org_url:
        If provided, ``--organization`` is appended.
    project:
        If provided, ``--project`` is appended.
    """
    cmd = ["az", *parts, "--output", "json"]
    if org_url:
        cmd.extend(["--organization", org_url])
    if project:
        cmd.extend(["--project", project])

    return retry(
        _run_az,
        cmd,
        timeout=timeout,
        parse_json=parse_json,
        max_retries=max_retries,
        retryable=(AzCliThrottled, subprocess.TimeoutExpired),
    )


def invoke(
    area: str,
    resource: str,
    *,
    route_parameters: dict[str, str] | None = None,
    query_parameters: dict[str, str] | None = None,
    http_method: str = "GET",
    api_version: str = "",
    org_url: str = "",
    project: str = "",
    timeout: int = 120,
    max_retries: int = 3,
    paginate: bool = True,
    max_pages: int = 100,
    list_key: str = "value",
) -> Any:
    """Call ``az devops invoke`` for REST operations without native subcommands.

    When *paginate* is True (the default) and the response contains a
    ``continuationToken``, additional pages are fetched automatically up to
    *max_pages*.  Items from each page are merged into a single list under
    *list_key* (default ``"value"``).
    """
    def _single_invoke(
        qp: dict[str, str] | None,
    ) -> Any:
        cmd = [
            "az",
            "devops",
            "invoke",
            "--area",
            area,
            "--resource",
            resource,
            "--http-method",
            http_method,
            "--output",
            "json",
        ]
        if api_version:
            cmd.extend(["--api-version", api_version])
        if route_parameters:
            pairs = [f"{k}={v}" for k, v in route_parameters.items()]
            cmd.extend(["--route-parameters", *pairs])
        if qp:
            pairs = [f"{k}={v}" for k, v in qp.items()]
            cmd.extend(["--query-parameters", *pairs])
        if org_url:
            cmd.extend(["--organization", org_url])
        if project:
            cmd.extend(["--project", project])

        return retry(
            _run_az,
            cmd,
            timeout=timeout,
            parse_json=True,
            max_retries=max_retries,
            retryable=(AzCliThrottled, subprocess.TimeoutExpired),
        )

    # First page
    result = _single_invoke(query_parameters)

    if not paginate or not isinstance(result, dict):
        return result

    # Collect paginated results
    all_items: list[Any] = []
    items = result.get(list_key, result)
    if isinstance(items, list):
        all_items.extend(items)
    else:
        return result  # Not a paginated list response

    token = result.get("continuationToken")
    page = 1
    while token and page < max_pages:
        page += 1
        qp = dict(query_parameters) if query_parameters else {}
        qp["continuationToken"] = token
        page_result = _single_invoke(qp)
        if not isinstance(page_result, dict):
            break
        page_items = page_result.get(list_key, [])
        if isinstance(page_items, list):
            all_items.extend(page_items)
        token = page_result.get("continuationToken")
        logger.debug("Pagination: page %d fetched %d items", page, len(page_items) if isinstance(page_items, list) else 0)

    # Return in the same envelope shape, minus the token
    result[list_key] = all_items
    result.pop("continuationToken", None)
    return result


def download_binary(
    url: str,
    dest: Path,
    *,
    timeout: int = 120,
    max_retries: int = 3,
) -> None:
    """Download binary content from a URL to *dest* using ``az rest``.

    Uses the currently authenticated az CLI session so no explicit credential
    handling is needed. The destination directory is created automatically.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["az", "rest", "--method", "GET", "--url", url, "--output-file", str(dest)]

    retry(
        _run_az,
        cmd,
        timeout=timeout,
        parse_json=False,
        max_retries=max_retries,
        retryable=(AzCliThrottled, subprocess.TimeoutExpired),
    )
    logger.debug("Downloaded binary → %s", dest)


def git_clone(
    repo_url: str,
    dest: Path,
    *,
    pat: str = "",
    timeout: int = 600,
) -> None:
    """Clone a Git repository to *dest* using the Git CLI.

    The PAT is passed via ``GIT_CONFIG_*`` environment variables so that it
    never appears in the process argument list (visible in ``/proc/<pid>/cmdline``
    or ``ps`` output).
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Pass PAT via git config env vars — keeps creds out of argv and ps output
    env = os.environ.copy()
    if pat and "://" in repo_url:
        token_b64 = base64.b64encode(f"x-token:{pat}".encode()).decode()
        # Strip path from URL to build the config scope key
        scheme, rest = repo_url.split("://", 1)
        host_part = rest.split("/")[0]
        scope_url = f"{scheme}://{host_part}/"
        env["GIT_CONFIG_COUNT"] = "1"
        env["GIT_CONFIG_KEY_0"] = f"http.{scope_url}.extraheader"
        env["GIT_CONFIG_VALUE_0"] = f"Authorization: Basic {token_b64}"

    # If dest already exists as a bare repo, fetch (incremental) instead of clone
    if (dest / "HEAD").exists():
        logger.info("Updating existing mirror %s", dest)
        cmd = ["git", "-C", str(dest), "remote", "update", "--prune"]
    else:
        logger.info("Cloning %s -> %s", repo_url, dest)
        cmd = ["git", "clone", "--mirror", repo_url, str(dest)]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    if result.returncode != 0:
        safe_stderr = _scrub_pat(result.stderr, pat)
        raise AzCliError(
            f"git operation failed (rc={result.returncode}): {safe_stderr.strip()}",
            result.returncode,
            safe_stderr.strip(),
        )


def _scrub_pat(text: str, pat: str) -> str:
    """Remove any occurrence of the PAT from *text*."""
    if not pat:
        return text
    return text.replace(pat, "***")
