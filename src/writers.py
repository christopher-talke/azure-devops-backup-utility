"""JSON and binary writers with atomic writes."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _secure_mkdir(path: Path) -> None:
    """Create directory tree with restricted permissions (0o700 on Unix)."""
    path.mkdir(parents=True, exist_ok=True)
    if sys.platform != "win32":
        # Walk up and tighten any directories we just created
        for parent in [path, *path.parents]:
            try:
                os.chmod(parent, 0o700)
            except OSError:
                break  # reached a dir we don't own


def write_json(path: Path, data: Any) -> None:
    """Atomically write *data* as pretty-printed JSON to *path*."""
    _secure_mkdir(path.parent)
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
    _secure_mkdir(path.parent)
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
    _secure_mkdir(path.parent)
    with open(path, "a", encoding="utf-8") as fh:
        json.dump(record, fh, sort_keys=True, default=str)
        fh.write("\n")


def file_hash(path: Path, algorithm: str = "sha256") -> str:
    """Return the hex digest of *path* using the given hash algorithm."""
    h = hashlib.new(algorithm)
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
