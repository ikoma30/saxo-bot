"""
Unit tests for the exceptions module.
"""

from src.common.exceptions import SaxoApiError


class TestSaxoApiError:
    """Test suite for the SaxoApiError class."""

    def test_init_with_message_only(self) -> None:
        """Test initialization with message only."""
        error = SaxoApiError("Test error")
        assert str(error) == "Test error"
        assert error.status_code is None
        assert error.response_body is None

    def test_init_with_status_code(self) -> None:
        """Test initialization with status code."""
        error = SaxoApiError("Test error", 404)
        assert str(error) == "Test error (Status Code: 404)"
        assert error.status_code == 404
        assert error.response_body is None

    def test_init_with_response_body(self) -> None:
        """Test initialization with response body."""
        response_body = {"error": "Not found"}
        error = SaxoApiError("Test error", 404, response_body)
        assert str(error) == "Test error (Status Code: 404)"
        assert error.status_code == 404
        assert error.response_body == response_body
