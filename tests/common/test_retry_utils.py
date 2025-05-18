"""
Unit tests for the retry_utils module.
"""

from time import sleep
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.common.exceptions import SaxoApiError
from src.common.retry_utils import calculate_wait_time, retryable


class TestRetryUtils:
    """Test suite for the retry_utils module."""

    def test_calculate_wait_time(self) -> None:
        """Test calculate_wait_time function."""
        with patch("random.uniform", return_value=0.1):
            wait_time = calculate_wait_time(1, 2.0, 0.2)
            assert wait_time == 1.1  # 2.0^0 + 0.1

            wait_time = calculate_wait_time(2, 2.0, 0.2)
            assert wait_time == 2.2  # 2.0^1 + 0.2

            wait_time = calculate_wait_time(3, 2.0, 0.2)
            assert wait_time == 4.4  # 2.0^2 + 0.4

    @patch("time.sleep")
    def test_retryable_success_first_try(self, mock_sleep: MagicMock) -> None:
        """Test retryable decorator with success on first try."""
        mock_func = MagicMock(return_value="success")
        decorated_func = retryable()(mock_func)

        result = decorated_func("arg1", kwarg1="kwarg1")

        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="kwarg1")
        mock_sleep.assert_not_called()

    @patch("time.sleep")
    def test_retryable_success_after_retry(self, mock_sleep: MagicMock) -> None:
        """Test retryable decorator with success after retry."""
        mock_func = MagicMock(side_effect=[requests.RequestException("Error"), "success"])
        decorated_func = retryable()(mock_func)

        result = decorated_func("arg1", kwarg1="kwarg1")

        assert result == "success"
        assert mock_func.call_count == 2
        mock_sleep.assert_called_once()

    @patch("time.sleep")
    def test_retryable_all_attempts_fail(self, mock_sleep: MagicMock) -> None:
        """Test retryable decorator with all attempts failing."""
        error = requests.RequestException("Error")
        mock_func = MagicMock(side_effect=[error, error, error])
        decorated_func = retryable(max_attempts=3)(mock_func)

        with pytest.raises(requests.RequestException) as excinfo:
            decorated_func("arg1", kwarg1="kwarg1")

        assert str(excinfo.value) == "Error"
        assert mock_func.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("time.sleep")
    def test_retryable_with_custom_exceptions(self, mock_sleep: MagicMock) -> None:
        """Test retryable decorator with custom exceptions."""
        error = SaxoApiError("API Error")
        mock_func = MagicMock(side_effect=[error, "success"])
        decorated_func = retryable(exceptions=[SaxoApiError])(mock_func)

        result = decorated_func("arg1", kwarg1="kwarg1")

        assert result == "success"
        assert mock_func.call_count == 2
        mock_sleep.assert_called_once()

    @patch("time.sleep")
    def test_retryable_with_response_status_code(self, mock_sleep: MagicMock) -> None:
        """Test retryable decorator with response status code."""
        mock_response_429 = MagicMock(spec=requests.Response)
        mock_response_429.status_code = 429
        mock_response_200 = MagicMock(spec=requests.Response)
        mock_response_200.status_code = 200

        mock_func = MagicMock(side_effect=[mock_response_429, mock_response_200])
        decorated_func = retryable(statuses=[429])(mock_func)

        result = decorated_func("arg1", kwarg1="kwarg1")

        assert result == mock_response_200
        assert mock_func.call_count == 2
        mock_sleep.assert_called_once()

    @patch("time.sleep")
    def test_retryable_with_custom_backoff(self, mock_sleep: MagicMock) -> None:
        """Test retryable decorator with custom backoff factor."""
        error = requests.RequestException("Error")
        mock_func = MagicMock(side_effect=[error, "success"])
        decorated_func = retryable(backoff_factor=3.0)(mock_func)

        with patch("src.common.retry_utils.calculate_wait_time") as mock_calculate:
            mock_calculate.return_value = 3.0
            result = decorated_func("arg1", kwarg1="kwarg1")

        assert result == "success"
        assert mock_func.call_count == 2
        mock_sleep.assert_called_once_with(3.0)
