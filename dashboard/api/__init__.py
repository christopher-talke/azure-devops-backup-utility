"""Shared helpers for the ADO Backup Dashboard Azure Function."""

import json
import os
import time

from azure.storage.blob import ContainerClient

_container_client = None

# In-memory cache: {"data": [...], "expires": float}
_backup_list_cache = {"data": None, "expires": 0.0}
_CACHE_TTL_SECONDS = 300  # 5 minutes


def get_container_client() -> ContainerClient:
    """Return a ContainerClient, creating it on first call."""
    global _container_client
    if _container_client is not None:
        return _container_client

    conn_str = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    account_url = os.environ.get("AZURE_STORAGE_ACCOUNT_URL")
    container = os.environ.get("AZURE_STORAGE_CONTAINER", "ado-backups")

    if conn_str:
        _container_client = ContainerClient.from_connection_string(
            conn_str, container_name=container
        )
    elif account_url:
        from azure.identity import DefaultAzureCredential

        _container_client = ContainerClient(
            account_url, container_name=container,
            credential=DefaultAzureCredential()
        )
    else:
        raise RuntimeError(
            "Set AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_ACCOUNT_URL"
        )

    return _container_client


def download_blob_text(blob_path: str) -> str | None:
    """Download a blob as UTF-8 text.  Returns None if the blob does not exist."""
    client = get_container_client()
    try:
        return client.download_blob(blob_path).readall().decode("utf-8")
    except Exception:
        return None


def download_blob_json(blob_path: str):
    """Download a blob and parse it as JSON.  Returns None on missing/invalid."""
    text = download_blob_text(blob_path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def discover_backups(*, force_refresh: bool = False) -> list[dict]:
    """List all backup runs by scanning for _indexes/manifest.json blobs.

    Results are cached in-memory for ``_CACHE_TTL_SECONDS``.
    """
    now = time.time()
    if (
        not force_refresh
        and _backup_list_cache["data"] is not None
        and now < _backup_list_cache["expires"]
    ):
        return _backup_list_cache["data"]

    client = get_container_client()
    backups: list[dict] = []

    # Walk blobs looking for _indexes/manifest.json files.
    for blob in client.list_blobs(name_starts_with=""):
        if not blob.name.endswith("_indexes/manifest.json"):
            continue

        # blob.name looks like: dev.azure.com/myorg/20260410T020000Z/_indexes/manifest.json
        # Strip the trailing _indexes/manifest.json to get the backup prefix.
        prefix = blob.name.rsplit("_indexes/manifest.json", 1)[0].rstrip("/")
        parts = prefix.split("/")
        if len(parts) < 3:
            continue

        host = parts[0]
        org = parts[1]
        timestamp = parts[2]

        manifest = download_blob_json(blob.name)
        if manifest is None:
            continue

        backups.append({
            "id": prefix,
            "host": host,
            "org": org,
            "timestamp": timestamp,
            "started_at": manifest.get("started_at", ""),
            "completed_at": manifest.get("completed_at", ""),
            "duration_seconds": manifest.get("duration_seconds", 0),
            "total_entities": manifest.get("total_entities", 0),
            "total_errors": manifest.get("total_errors", 0),
        })

    # Most recent first.
    backups.sort(key=lambda b: b["timestamp"], reverse=True)

    _backup_list_cache["data"] = backups
    _backup_list_cache["expires"] = now + _CACHE_TTL_SECONDS
    return backups
