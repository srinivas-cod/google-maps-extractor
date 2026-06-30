"""General-purpose utilities shared across the project."""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, Protocol, TypeVar


P = ParamSpec("P")
R = TypeVar("R")


class WaitablePage(Protocol):
    """Protocol representing the subset of page APIs required by wait helpers."""

    def wait_for_selector(self, selector: str, timeout: int | None = None) -> Any:
        """Wait until a selector is present and return its handle."""


def safe_sleep(seconds: int | float) -> None:
    """Pause execution for a non-negative number of seconds."""

    if seconds <= 0:
        return
    time.sleep(seconds)


def retry(
    *,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    attempts: int = 3,
    delay: int | float = 1,
    logger: logging.Logger | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry a function call when one of the provided exceptions is raised."""

    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_error: Exception | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return function(*args, **kwargs)
                except exceptions as error:
                    last_error = error
                    if logger is not None:
                        logger.warning(
                            "Retry %s/%s failed for %s: %s",
                            attempt,
                            attempts,
                            function.__name__,
                            error,
                        )
                    if attempt < attempts:
                        safe_sleep(delay)
            assert last_error is not None
            raise last_error

        return wrapper

    return decorator


def sanitize_filename(value: str, replacement: str = "_") -> str:
    """Sanitize a string so it can be safely used as a filename."""

    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1F]+', replacement, value).strip()
    sanitized = re.sub(r"\s+", " ", sanitized)
    return sanitized or "untitled"


def wait_for_element(
    page: WaitablePage,
    selector: str,
    timeout: int = 10000,
) -> Any:
    """Wait for a DOM element using a generic Playwright-compatible page object."""

    return page.wait_for_selector(selector, timeout=timeout)


def extract_coordinates(url: str | None) -> tuple[float | None, float | None]:
    """Extract latitude and longitude values from a Google Maps style URL."""

    if not url:
        return None, None

    match = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", url)
    if not match:
        return None, None

    latitude, longitude = match.groups()
    return float(latitude), float(longitude)


def time_execution(
    logger: logging.Logger,
    label: str,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Measure function execution time and send the result to the logger."""

    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start_time = time.perf_counter()
            try:
                return function(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start_time
                logger.info("%s completed in %.2f seconds", label, duration)

        return wrapper

    return decorator
