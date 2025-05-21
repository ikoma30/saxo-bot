"""
Unit tests for SaxoClient.
"""

import os
from unittest.mock import patch, MagicMock

import pytest

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


@patch("src.core.saxo_client.SaxoClient._get")
@patch("src.core.saxo_client.update_trade_status")
def test_wait_for_order_filled_success(mock_update_status: MagicMock, mock_get: MagicMock, saxo_client: SaxoClient) -> None:
    """Test wait_for_order_filled with successful fill."""
    mock_get.return_value = {"OrderId": "test-123", "Status": "Filled"}
    
    result = saxo_client.wait_for_order_filled("test-123", max_wait_seconds=5)
    
    assert result["Status"] == "Filled"
    mock_update_status.assert_called_once_with("Filled")
    mock_get.assert_called_once()


@patch("src.core.saxo_client.SaxoClient._get")
@patch("src.core.saxo_client.update_trade_status")
@patch("src.core.saxo_client.time.sleep")
def test_wait_for_order_filled_timeout(mock_sleep: MagicMock, mock_update_status: MagicMock, mock_get: MagicMock, saxo_client: SaxoClient) -> None:
    """Test wait_for_order_filled with timeout."""
    mock_get.return_value = {"OrderId": "test-123", "Status": "Working"}
    mock_sleep.return_value = None
    
    result = saxo_client.wait_for_order_filled("test-123", max_wait_seconds=3, poll_interval=1)
    
    assert result["Status"] == "Timeout"
    mock_update_status.assert_not_called()
    assert mock_get.call_count >= 2


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
