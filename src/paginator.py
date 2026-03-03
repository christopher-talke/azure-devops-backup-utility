"""Helpers for continuation-token based pagination."""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


def paginate(
    fetch: Callable[..., tuple[Any, str | None]],
    *args: Any,
    max_pages: int = 100,
    **kwargs: Any,
) -> list[Any]:
    """Collect all pages returned by *fetch*.

    *fetch* must return ``(result_list, continuation_token | None)``.
    Pagination stops when the token is ``None`` or *max_pages* is reached.
    """
    all_items: list[Any] = []
    token: str | None = None
    for page_num in range(1, max_pages + 1):
        items, token = fetch(*args, continuation_token=token, **kwargs)
        if isinstance(items, list):
            all_items.extend(items)
        else:
            all_items.append(items)
        logger.debug("Page %d returned %d items", page_num, len(items) if isinstance(items, list) else 1)
        if not token:
            break
    return all_items
