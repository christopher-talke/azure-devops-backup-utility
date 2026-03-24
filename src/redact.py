"""Redaction utilities for sensitive fields."""

from __future__ import annotations

import copy
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Field names whose values must be redacted before persisting.
# Both underscore-separated and concatenated forms are included so that
# keys like "access_token" as well as "accessToken" are caught after lowering.
SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "secret",
        "token",
        "privatekey",
        "private_key",
        "certificate",
        "apikey",
        "api_key",
        "accesstoken",
        "access_token",
        "connectionstring",
        "connection_string",
        "securefileid",
        "client_secret",
        "clientsecret",
        "sas_token",
        "sastoken",
        "encrypted_value",
        "encryptedvalue",
        "credentials",
        "subscription_key",
        "subscriptionkey",
    }
)

# Dot-separated paths that should always be redacted.
SENSITIVE_PATHS: frozenset[str] = frozenset(
    {
        "authorization.parameters",
        "configuration.value",
        "data.accesstoken",
    }
)

REDACTED = "***REDACTED***"

_SENSITIVE_KEYS_LOWER: frozenset[str] = frozenset(k.lower() for k in SENSITIVE_KEYS)


def _is_sensitive_key(key: str) -> bool:
    return key.lower().replace("-", "_") in _SENSITIVE_KEYS_LOWER


def _has_secret_sibling(data: dict[str, Any]) -> bool:
    """Return True if the dict has an explicit ``isSecret`` flag set to truthy."""
    return bool(data.get("isSecret") or data.get("issecret") or data.get("is_secret"))


def redact_dict(data: Any, *, _path: str = "") -> Any:
    """Return a deep copy of *data* with sensitive values replaced by ``REDACTED``.

    Works recursively on dicts and lists.  In addition to key-name matching it
    also detects the Azure DevOps ``{"isSecret": true, "value": ...}`` pattern
    and redacts the ``value`` field.
    """
    if isinstance(data, dict):
        # Detect isSecret sibling pattern *before* iterating keys
        secret_sibling = _has_secret_sibling(data)
        out: dict[str, Any] = {}
        for key, value in data.items():
            current_path = f"{_path}.{key}" if _path else key
            if _is_sensitive_key(key):
                out[key] = REDACTED
            elif current_path.lower() in SENSITIVE_PATHS:
                out[key] = REDACTED
            elif secret_sibling and key.lower() == "value":
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
