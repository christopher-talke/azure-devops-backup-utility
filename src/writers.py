"""JSON and binary writers with atomic writes."""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def write_json(path: Path, data: Any) -> None:
    """Atomically write *data* as pretty-printed JSON to *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=path.parent, suffix=".tmp", prefix=path.stem
    )
    try:
        with open(tmp_fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True, default=str)
            fh.write("\n")
        Path(tmp_path).replace(path)
        logger.debug("Wrote %s", path)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def write_binary(path: Path, data: bytes) -> None:
    """Atomically write binary *data* to *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=path.parent, suffix=".tmp", prefix=path.stem
    )
    try:
        with open(tmp_fd, "wb") as fh:
            fh.write(data)
        Path(tmp_path).replace(path)
        logger.debug("Wrote %s", path)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append a single JSON record to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        json.dump(record, fh, sort_keys=True, default=str)
        fh.write("\n")
