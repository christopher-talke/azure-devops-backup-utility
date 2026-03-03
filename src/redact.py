"""Redaction utilities for sensitive fields."""

from __future__ import annotations

import copy
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Field names whose values must be redacted before persisting.
SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "secret",
        "token",
        "privatekey",
        "privateKey",
        "certificate",
        "apikey",
        "apiKey",
        "accesstoken",
        "accessToken",
        "connectionstring",
        "connectionString",
        "securefileid",
        "secureFileId",
    }
)

# Dot-separated paths that should always be redacted.
SENSITIVE_PATHS: frozenset[str] = frozenset(
    {
        "authorization.parameters",
    }
)

REDACTED = "***REDACTED***"


def _is_sensitive_key(key: str) -> bool:
    return key.lower() in {k.lower() for k in SENSITIVE_KEYS}


def redact_dict(data: Any, *, _path: str = "") -> Any:
    """Return a deep copy of *data* with sensitive values replaced by ``REDACTED``.

    Works recursively on dicts and lists.
    """
    if isinstance(data, dict):
        out: dict[str, Any] = {}
        for key, value in data.items():
            current_path = f"{_path}.{key}" if _path else key
            if _is_sensitive_key(key):
                out[key] = REDACTED
            elif current_path in SENSITIVE_PATHS:
                out[key] = REDACTED
            else:
                out[key] = redact_dict(value, _path=current_path)
        return out
    if isinstance(data, list):
        return [redact_dict(item, _path=_path) for item in data]
    return data


def redact(data: Any) -> Any:
    """Public entry point: deep-copy then redact."""
    return redact_dict(copy.deepcopy(data))
