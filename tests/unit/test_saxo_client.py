"""
Unit tests for SaxoClient.
"""

import os
from unittest.mock import patch, MagicMock

import pytest

from src.common.exceptions import OrderPollingTimeoutError
from src.core.saxo_client import SaxoClient


@pytest.fixture
def saxo_client() -> SaxoClient:
    """Return a SaxoClient instance for testing."""
    return SaxoClient(environment="sim")


@patch("src.core.saxo_client.SaxoClient._post")
def test_place_order_v3(mock_post: MagicMock, saxo_client: SaxoClient) -> None:
    """Test place_order with USE_TRADE_V3=true."""
    mock_post.return_value = {"OrderId": "test-123", "Status": "Placed"}
    os.environ["USE_TRADE_V3"] = "true"

    saxo_client.access_token = "test-token"
    saxo_client.account_key = "test-account"

    result = saxo_client.place_order("USDJPY", "Buy", 0.01)

    assert result is not None
    assert "OrderId" in result
    assert result["OrderId"] == "test-123"
    assert result["Status"] == "Placed"
    mock_post.assert_called_once()

    os.environ.pop("USE_TRADE_V3", None)


@patch("src.core.saxo_client.SaxoClient._post")
def test_place_order_v3_with_error_handling(mock_post: MagicMock, saxo_client: SaxoClient) -> None:
    """Test place_order with v3 API error handling."""
    mock_post.side_effect = Exception("Test error")
    os.environ["USE_TRADE_V3"] = "true"

    saxo_client.access_token = "test-token"
    saxo_client.account_key = "test-account"

    result = saxo_client.place_order("USDJPY", "Buy", 0.01)

    assert result is not None
    assert "OrderId" in result
    assert "Status" in result
    assert result["Status"] == "Placed"
    mock_post.assert_called_once()

    os.environ.pop("USE_TRADE_V3", None)


@patch("src.core.saxo_client.SaxoClient.wait_for_order_status")
@patch("src.core.saxo_client.update_trade_status")
def test_wait_for_order_filled_success(
    mock_update_status: MagicMock, mock_wait_for_status: MagicMock, saxo_client: SaxoClient
) -> None:
    """Test wait_for_order_filled with successful fill."""
    mock_wait_for_status.return_value = {"OrderId": "test-123", "Status": "Filled"}

    result = saxo_client.wait_for_order_filled("test-123", max_wait_seconds=5)

    assert result["Status"] == "Filled"
    mock_update_status.assert_called_once_with("Filled")
    mock_wait_for_status.assert_called_once_with(
        "test-123", 
        target_status=["Filled", "Executed"],
        failed_status=["Cancelled", "Expired", "Rejected"],
        max_wait_seconds=5, 
        poll_interval=2
    )


@patch("src.core.saxo_client.SaxoClient.wait_for_order_status")
@patch("src.core.saxo_client.update_trade_status")
def test_wait_for_order_filled_executed(
    mock_update_status: MagicMock, mock_wait_for_status: MagicMock, saxo_client: SaxoClient
) -> None:
    """Test wait_for_order_filled with executed status."""
    mock_wait_for_status.return_value = {"OrderId": "test-123", "Status": "Executed"}

    result = saxo_client.wait_for_order_filled("test-123", max_wait_seconds=5)

    assert result["Status"] == "Executed"
    mock_update_status.assert_called_once_with("Executed")
    mock_wait_for_status.assert_called_once_with(
        "test-123", 
        target_status=["Filled", "Executed"],
        failed_status=["Cancelled", "Expired", "Rejected"],
        max_wait_seconds=5, 
        poll_interval=2
    )


@patch("src.core.saxo_client.SaxoClient.wait_for_order_status")
@patch("src.core.saxo_client.update_trade_status")
def test_wait_for_order_filled_timeout(
    mock_update_status: MagicMock,
    mock_wait_for_status: MagicMock,
    saxo_client: SaxoClient,
) -> None:
    """Test wait_for_order_filled with timeout."""
    mock_wait_for_status.side_effect = OrderPollingTimeoutError("test-123", 3.0, "Working")

    result = saxo_client.wait_for_order_filled("test-123", max_wait_seconds=3, poll_interval=1)

    assert result["Status"] == "Timeout"
    mock_update_status.assert_not_called()
    mock_wait_for_status.assert_called_once_with(
        "test-123", 
        target_status=["Filled", "Executed"],
        failed_status=["Cancelled", "Expired", "Rejected"],
        max_wait_seconds=3, 
        poll_interval=1
    )


@patch("src.core.saxo_client.SaxoClient._get_instrument_uic")
def test_build_market_order_body(mock_get_uic: MagicMock, saxo_client: SaxoClient) -> None:
    """Test _build_market_order_body method."""
    mock_get_uic.return_value = 1

    result = saxo_client._build_market_order_body("USDJPY", "Buy", 0.01)

    assert result["OrderType"] == "Market"
    assert result["AssetType"] == "FxSpot"
    assert result["BuySell"] == "Buy"
    assert result["Amount"] == "0.01"
    assert result["AmountType"] == "Lots"
    assert "OrderDuration" in result
    assert result["OrderDuration"]["DurationType"] == "DayOrder"


@patch("src.core.saxo_client.SaxoClient._get_instrument_uic")
def test_build_market_order_body_sell(mock_get_uic: MagicMock, saxo_client: SaxoClient) -> None:
    """Test building a market order body for sell orders."""
    mock_get_uic.return_value = 21

    order_body = saxo_client._build_market_order_body("USDJPY", "Sell", 0.01)

    assert order_body["OrderType"] == "Market"
    assert order_body["AssetType"] == "FxSpot"
    assert order_body["BuySell"] == "Sell"
    assert order_body["Amount"] == "0.01"
    assert order_body["AmountType"] == "Lots"
    assert order_body["Uic"] == 21
    assert "OrderDuration" in order_body
    assert order_body["OrderDuration"]["DurationType"] == "DayOrder"


@patch("src.core.saxo_client.SaxoClient.get_order_status")
def test_wait_for_order_status(mock_get_status: MagicMock, saxo_client: SaxoClient) -> None:
    """Test wait_for_order_status method."""
    mock_get_status.return_value = {"OrderId": "test-123", "Status": "Filled"}

    saxo_client.access_token = "test-token"
    saxo_client.account_key = "test-account"

    result = saxo_client.wait_for_order_status(
        "test-123", target_status=["Filled", "Executed"], max_wait_seconds=5
    )

    assert result is not None
    assert result["Status"] == "Filled"
    mock_get_status.assert_called_once()


@patch("src.core.saxo_client.SaxoClient.get_order_status")
def test_wait_for_order_status_timeout(mock_get_status: MagicMock, saxo_client: SaxoClient) -> None:
    """Test wait_for_order_status method with timeout."""
    mock_get_status.return_value = {"OrderId": "test-123", "Status": "Working"}

    saxo_client.access_token = "test-token"
    saxo_client.account_key = "test-account"

    with pytest.raises(OrderPollingTimeoutError) as excinfo:
        saxo_client.wait_for_order_status(
            "test-123", target_status=["Filled", "Executed"], max_wait_seconds=5
        )

    assert "Order test-123 polling timed out" in str(excinfo.value)
    assert "Working" in str(excinfo.value)
    assert mock_get_status.call_count > 1
