"""Retry with exponential backoff and jitter."""

import logging
import random
import time
from typing import Any, Callable, Sequence, Type

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = 5
DEFAULT_BASE_DELAY = 1.0
DEFAULT_MAX_DELAY = 60.0


def retry(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    retryable: Sequence[Type[Exception]] = (Exception,),
    **kwargs: Any,
) -> Any:
    """Call *func* with retries using exponential backoff and jitter.

    Parameters
    ----------
    func:
        The callable to invoke.
    max_retries:
        Maximum number of retry attempts.
    base_delay:
        Initial delay in seconds.
    max_delay:
        Upper bound for computed delay.
    retryable:
        Tuple of exception types that should trigger a retry.
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except tuple(retryable) as exc:
            last_exc = exc
            if attempt == max_retries:
                logger.error("All %d attempts failed for %s", max_retries, func.__name__)
                raise
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            jitter = random.uniform(0, delay * 0.5)  # noqa: S311
            sleep_time = delay + jitter
            logger.warning(
                "Attempt %d/%d for %s failed (%s). Retrying in %.1fs …",
                attempt,
                max_retries,
                func.__name__,
                exc,
                sleep_time,
            )
            time.sleep(sleep_time)
    raise last_exc  # type: ignore[misc]
