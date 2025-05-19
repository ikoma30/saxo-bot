"""
Exceptions for Saxo Bot.

This module provides custom exceptions for the Saxo Bot system.
"""

from typing import Any


class SaxoApiError(Exception):
    """Exception raised for errors in the Saxo Bank API responses."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize SaxoApiError.

        Args:
            message: Error message
            status_code: HTTP status code
            response_body: Full response body from the API
        """
        self.status_code = status_code
        self.response_body = response_body
        error_msg = f"{message}"
        if status_code:
            error_msg += f" (Status Code: {status_code})"
        super().__init__(error_msg)


class OrderRejected(SaxoApiError):
    """Exception raised when an order is rejected."""

    def __init__(
        self, 
        message: str, 
        reason: str, 
        status_code: int | None = None, 
        response_body: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize the exception.

        Args:
            message: The error message
            reason: The reason for rejection
            status_code: HTTP status code
            response_body: Full response body from the API
        """
        self.reason = reason
        super().__init__(f"{message}: {reason}", status_code, response_body)
