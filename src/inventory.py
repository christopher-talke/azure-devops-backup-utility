"""Builds manifest and inventory indexes."""

from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
from typing import Any

import writers

logger = logging.getLogger(__name__)


class Inventory:
    """Tracks exported entities and builds the final manifest."""

    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []
        self.limits: dict[str, Any] = {}
        self.start_time = datetime.datetime.now(datetime.timezone.utc)

    def add(self, category: str, name: str, path: str, count: int = 1) -> None:
        self.entries.append(
            {
                "category": category,
                "name": name,
                "path": path,
                "count": count,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
        )

    def add_error(self, category: str, name: str, error: str, detail: str = "", *, pat: str = "") -> None:
        if pat:
            error = error.replace(pat, "***")
            detail = detail.replace(pat, "***")
        record = {
            "category": category,
            "name": name,
            "error": error,
            "detail": detail,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        self.errors.append(record)

    def set_limits(self, limits: dict[str, Any]) -> None:
        self.limits = limits

    def write(self, inventory_path: Path, manifest_path: Path, errors_path: Path) -> None:
        end_time = datetime.datetime.now(datetime.timezone.utc)
        manifest = {
            "tool": "ado-backup",
            "version": "0.1.0",
            "started_at": self.start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "duration_seconds": (end_time - self.start_time).total_seconds(),
            "total_entities": len(self.entries),
            "total_errors": len(self.errors),
            "limits_applied": self.limits,
        }
        writers.write_json(manifest_path, manifest)
        writers.write_json(inventory_path, self.entries)
        # Write errors as JSONL
        if self.errors:
            for err in self.errors:
                writers.append_jsonl(errors_path, err)
        logger.info(
            "Manifest written: %d entities, %d errors", len(self.entries), len(self.errors)
        )
