# ruff: noqa: S311
"""
Retry utilities for Saxo Bot.

This module provides utilities for retrying operations with exponential backoff
and jitter, as specified in the Saxo OpenAPI documentation.
"""

import logging
import random  # nosec B311
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

import requests

from src.common.exceptions import SaxoApiError

logger = logging.getLogger("saxo")

T = TypeVar("T")


def retryable(
    max_attempts: int = 3,
    statuses: list[int] | None = None,
    backoff_factor: float = 2.0,
    jitter_factor: float = 0.2,
    exceptions: list[type[Exception]] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying operations with exponential backoff and jitter.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        statuses: List of HTTP status codes to retry on (default: [429, 502, 503, 504])
        backoff_factor: Base factor for exponential backoff (default: 2.0)
        jitter_factor: Factor for jitter (default: 0.2)
        exceptions: List of exceptions to retry on (default: [requests.RequestException])

    Returns:
        Decorated function that will retry on specified conditions
    """
    if statuses is None:
        statuses = [429, 502, 503, 504]
    if exceptions is None:
        exceptions = [requests.RequestException, SaxoApiError]

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    
                    if isinstance(result, requests.Response) and result.status_code in statuses:
                        wait_time = calculate_wait_time(attempt, backoff_factor, jitter_factor)
                        logger.warning(
                            f"Received status code {result.status_code}, retrying in "
                            f"{wait_time:.2f}s (attempt {attempt}/{max_attempts})"
                        )
                        time.sleep(wait_time)
                        continue
                    
                    return result
                except tuple(exceptions) as e:
                    last_exception = e
                    wait_time = calculate_wait_time(attempt, backoff_factor, jitter_factor)
                    logger.warning(
                        f"Request failed with {e.__class__.__name__}: {str(e)}, retrying in "
                        f"{wait_time:.2f}s (attempt {attempt}/{max_attempts})"
                    )
                    
                    if attempt < max_attempts:
                        time.sleep(wait_time)
            
            if last_exception:
                logger.error(
                    f"All {max_attempts} retry attempts failed with "
                    f"{last_exception.__class__.__name__}: {str(last_exception)}"
                )
                raise last_exception
            
            raise RuntimeError("Unexpected error in retry logic")
        
        return cast(Callable[..., T], wrapper)
    
    return decorator


def calculate_wait_time(attempt: int, backoff_factor: float, jitter_factor: float) -> float:
    """
    Calculate wait time with exponential backoff and jitter.

    Args:
        attempt: Current attempt number (1-based)
        backoff_factor: Base factor for exponential backoff
        jitter_factor: Factor for jitter

    Returns:
        Wait time in seconds
    """
    base_wait = backoff_factor ** (attempt - 1)
    
    # Not used for cryptographic purposes, only for adding jitter to retry timings
    jitter = random.uniform(-jitter_factor, jitter_factor) * base_wait  # nosec B311
    
    return base_wait + jitter
