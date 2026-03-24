"""Thin wrapper around az CLI and az devops invoke calls."""

from __future__ import annotations

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
        if re.search(r"5\d{2}", stderr):
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
) -> Any:
    """Call ``az devops invoke`` for REST operations without native subcommands."""
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
    if query_parameters:
        pairs = [f"{k}={v}" for k, v in query_parameters.items()]
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


def git_clone(
    repo_url: str,
    dest: Path,
    *,
    pat: str = "",
    timeout: int = 600,
) -> None:
    """Clone a Git repository to *dest* using the Git CLI."""
    # Inject PAT into URL for authentication
    if pat and "://" in repo_url:
        scheme, rest = repo_url.split("://", 1)
        auth_url = f"{scheme}://x-token:{pat}@{rest}"
    else:
        auth_url = repo_url

    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone", "--mirror", auth_url, str(dest)]
    # Log without secret
    logger.info("Cloning %s -> %s", repo_url, dest)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        safe_stderr = result.stderr.replace(pat, "***") if pat else result.stderr
        raise AzCliError(
            f"git clone failed (rc={result.returncode}): {safe_stderr.strip()}",
            result.returncode,
            safe_stderr.strip(),
        )
