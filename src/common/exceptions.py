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


class OrderPollingTimeoutError(Exception):
    """
    Raised when order polling times out without reaching a terminal status.
    
    According to Parent Spec §7.2.3, this should be raised when order polling
    exceeds the maximum wait time without reaching a terminal status.
    """
    
    def __init__(self, order_id: str, elapsed_time: float, last_status: str):
        """
        Initialize OrderPollingTimeoutError.
        
        Args:
            order_id: The ID of the order that timed out
            elapsed_time: The time spent polling in seconds
            last_status: The last known status of the order
        """
        self.order_id = order_id
        self.elapsed_time = elapsed_time
        self.last_status = last_status
        message = f"Order {order_id} polling timed out after {elapsed_time:.2f}s with status '{last_status}'"
        super().__init__(message)
