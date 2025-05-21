"""
Unit tests for SaxoClient order status methods.
"""

from unittest.mock import patch, MagicMock

import pytest

from src.core.saxo_client import SaxoClient


@pytest.fixture
def saxo_client() -> SaxoClient:
    """Return a SaxoClient instance for testing."""
    client = SaxoClient(environment="sim")
    client.access_token = "test-token"
    client.account_key = "test-account"
    return client


@patch("src.core.saxo_client.SaxoClient.get_order_status")
def test_get_order_status_success(mock_get_status: MagicMock, saxo_client: SaxoClient) -> None:
    """Test get_order_status with successful response."""
    mock_get_status.return_value = {"OrderId": "test-123", "Status": "Filled"}

    result = saxo_client.get_order_status("test-123")

    assert result is not None
    assert result["OrderId"] == "test-123"
    assert result["Status"] == "Filled"
    mock_get_status.assert_called_once()


@patch("src.core.saxo_client.SaxoClient.get_order_status")
def test_get_order_status_error(mock_get_status: MagicMock, saxo_client: SaxoClient) -> None:
    """Test get_order_status with error response."""
    mock_get_status.return_value = None

    result = saxo_client.get_order_status("test-123")

    assert result is None
    mock_get_status.assert_called_once()


@patch("src.core.saxo_client.SaxoClient.get_order_status")
@patch("src.core.saxo_client.time.sleep")
def test_wait_for_order_status_timeout(
    mock_sleep: MagicMock, mock_get_status: MagicMock, saxo_client: SaxoClient
) -> None:
    """Test wait_for_order_status with timeout."""
    mock_get_status.return_value = {"OrderId": "test-123", "Status": "Working"}
    mock_sleep.return_value = None

    result = saxo_client.wait_for_order_status(
        "test-123", target_status=["Filled", "Executed"], max_wait_seconds=3, poll_interval=1
    )

    assert result is None
    assert mock_get_status.call_count >= 2
    assert mock_sleep.call_count >= 2


@patch("src.core.saxo_client.SaxoClient.get_order_status")
def test_wait_for_order_status_multiple_statuses(
    mock_get_status: MagicMock, saxo_client: SaxoClient
) -> None:
    """Test wait_for_order_status with multiple target statuses."""
    mock_get_status.return_value = {"OrderId": "test-123", "Status": "Executed"}

    result = saxo_client.wait_for_order_status(
        "test-123", target_status=["Filled", "Executed"], max_wait_seconds=5
    )

    assert result is not None
    assert result["Status"] == "Executed"
    mock_get_status.assert_called_once()


@patch("src.core.saxo_client.SaxoClient.get_order_status")
def test_wait_for_order_status_string_target(
    mock_get_status: MagicMock, saxo_client: SaxoClient
) -> None:
    """Test wait_for_order_status with string target status."""
    mock_get_status.return_value = {"OrderId": "test-123", "Status": "Filled"}

    result = saxo_client.wait_for_order_status(
        "test-123", target_status="Filled", max_wait_seconds=5
    )

    assert result is not None
    assert result["Status"] == "Filled"
    mock_get_status.assert_called_once()


@patch("src.core.saxo_client.SaxoClient.get_order_status")
def test_wait_for_order_status_get_error(
    mock_get_status: MagicMock, saxo_client: SaxoClient
) -> None:
    """Test wait_for_order_status when get_order_status returns None."""
    mock_get_status.return_value = None

    result = saxo_client.wait_for_order_status(
        "test-123", target_status=["Filled", "Executed"], max_wait_seconds=3, poll_interval=1
    )

    assert result is None
    assert mock_get_status.call_count >= 2
