"""
Unit tests for the http_utils module.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.common.http_utils import _request_429, _request_5xx, request


class TestHttpUtils:
    """Test suite for the http_utils module."""

    @patch("requests.request")
    def test_request_429_success(self, mock_request: MagicMock) -> None:
        """Test _request_429 function with successful request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        result = _request_429("GET", "https://example.com")

        assert result == mock_response  # nosec: B101 # pytest assertion
        mock_request.assert_called_once_with("GET", "https://example.com")

    @patch("requests.request")
    def test_request_5xx_success(self, mock_request: MagicMock) -> None:
        """Test _request_5xx function with successful request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        result = _request_5xx("POST", "https://example.com", json={"key": "value"})

        assert result == mock_response  # nosec: B101 # pytest assertion
        mock_request.assert_called_once_with("POST", "https://example.com", json={"key": "value"})

    @patch("src.common.http_utils._request_429")
    def test_request_success(self, mock_request_429: MagicMock) -> None:
        """Test request function with successful request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request_429.return_value = mock_response

        result = request("GET", "https://example.com")

        assert result == mock_response  # nosec: B101 # pytest assertion
        mock_request_429.assert_called_once_with("GET", "https://example.com")

    @patch("src.common.http_utils._request_429")
    @patch("src.common.http_utils._request_5xx")
    def test_request_429_retry(self, mock_request_5xx: MagicMock, mock_request_429: MagicMock) -> None:
        """Test request function with 429 status code."""
        mock_error_response = MagicMock()
        mock_error_response.status_code = 429
        
        mock_http_error = requests.HTTPError("Too Many Requests")
        mock_http_error.response = mock_error_response
        
        mock_request_429.side_effect = mock_http_error
        
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_request_5xx.return_value = mock_success_response
        
        with patch("time.sleep"):
            with pytest.raises(requests.HTTPError):
                request("GET", "https://example.com")
        
        mock_request_429.assert_called_once_with("GET", "https://example.com")
        mock_request_5xx.assert_not_called()

    @patch("src.common.http_utils._request_429")
    @patch("src.common.http_utils._request_5xx")
    def test_request_5xx_retry(self, mock_request_5xx: MagicMock, mock_request_429: MagicMock) -> None:
        """Test request function with 5xx status code."""
        mock_error_response = MagicMock()
        mock_error_response.status_code = 503
        
        mock_request_429.side_effect = requests.HTTPError("Service Unavailable")
        mock_request_429.side_effect.response = mock_error_response

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request_5xx.return_value = mock_response

        with patch("time.sleep"):
            result = request("GET", "https://example.com")

        assert result == mock_response  # nosec: B101 # pytest assertion
        mock_request_429.assert_called_once_with("GET", "https://example.com")
        mock_request_5xx.assert_called_once_with("GET", "https://example.com")

    @patch("src.common.http_utils._request_429")
    @patch("src.common.http_utils._request_5xx")
    def test_request_other_error(self, mock_request_5xx: MagicMock, mock_request_429: MagicMock) -> None:
        """Test request function with non-retryable error."""
        mock_error_response = MagicMock()
        mock_error_response.status_code = 400
        
        error = requests.HTTPError("Bad Request")
        error.response = mock_error_response
        mock_request_429.side_effect = error

        with pytest.raises(requests.HTTPError) as excinfo:
            request("GET", "https://example.com")

        assert "Bad Request" in str(excinfo.value)  # nosec: B101 # pytest assertion
        mock_request_429.assert_called_once_with("GET", "https://example.com")
        mock_request_5xx.assert_not_called()
