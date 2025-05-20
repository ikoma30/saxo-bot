"""
HTTP utilities for Saxo Bot.

This module provides utilities for making HTTP requests to the Saxo OpenAPI.
"""

import logging
from typing import Any

import requests
from requests.models import Response

from src.common.retry_utils import retryable

logger = logging.getLogger("saxo")


@retryable(max_attempts=3, statuses=[429], backoff_factor=1.0, jitter_factor=0.2)
def _request_429(
    method: str,
    url: str,
    **kwargs: Any,
) -> Response:
    """
    Make an HTTP request with retry logic for 429 status code.

    Args:
        method: HTTP method (e.g., "GET", "POST")
        url: URL to request
        **kwargs: Additional arguments to pass to requests.request()

    Returns:
        requests.Response: The HTTP response

    Raises:
        SaxoApiError: If the request fails and all retries are exhausted
    """
    return requests.request(method, url, **kwargs)


@retryable(max_attempts=4, statuses=[502, 503, 504], backoff_factor=1.0, jitter_factor=0.2)
def _request_5xx(
    method: str,
    url: str,
    **kwargs: Any,
) -> Response:
    """
    Make an HTTP request with retry logic for 5xx status codes.

    Args:
        method: HTTP method (e.g., "GET", "POST")
        url: URL to request
        **kwargs: Additional arguments to pass to requests.request()

    Returns:
        requests.Response: The HTTP response

    Raises:
        SaxoApiError: If the request fails and all retries are exhausted
    """
    return requests.request(method, url, **kwargs)


def request(
    method: str,
    url: str,
    **kwargs: Any,
) -> Response:
    """
    Make an HTTP request with appropriate retry logic based on status code.

    Args:
        method: HTTP method (e.g., "GET", "POST")
        url: URL to request
        **kwargs: Additional arguments to pass to requests.request()

    Returns:
        requests.Response: The HTTP response

    Raises:
        SaxoApiError: If the request fails and all retries are exhausted
    """
    try:
        return _request_429(method, url, **kwargs)
    except requests.HTTPError as e:
        if hasattr(e, "response") and e.response is not None and e.response.status_code >= 500:
            return _request_5xx(method, url, **kwargs)
        raise
