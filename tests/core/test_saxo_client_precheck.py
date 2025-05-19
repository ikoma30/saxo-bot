"""
Tests for the SaxoClient precheck functionality.
"""

import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal

from src.core.saxo_client import SaxoClient
from src.common.exceptions import SaxoApiError, OrderRejected


class TestSaxoClientPrecheck:
    """Tests for the SaxoClient precheck functionality."""

    @patch("src.utils.uic_map.UICMap")
    def test_precheck_order_with_uic_mapping(self, mock_uic_map_class: MagicMock) -> None:
        """Test precheck_order with UIC mapping."""
        mock_uic_map = MagicMock()
        mock_uic_map.get_uic.return_value = 21
        mock_uic_map_class.return_value = mock_uic_map
        
        client = SaxoClient(environment="sim")
        client.access_token = "mock-token"
        client.account_key = "mock-account"
        
        client.get_quote = MagicMock(return_value={
            "Quote": {
                "Ask": "151.25",
                "Bid": "151.23"
            }
        })
        
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"PreCheckResult": "Accepted"}
            mock_post.return_value = mock_response
            mock_response.raise_for_status.return_value = None
            
            result = client._precheck_order("USDJPY", "Market", "Buy", Decimal("0.01"))
            
            mock_uic_map.get_uic.assert_called_once_with("USDJPY")
            
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert "/trade/v2/orders/precheck" in args[0]
            
            assert kwargs["json"]["Uic"] == 21
            assert kwargs["json"]["Amount"] == "1000"  # 0.01 lot converted to units
            
            assert result == {"PreCheckResult": "Accepted"}

    @patch("src.utils.uic_map.UICMap")
    def test_place_order_with_blocking_disclaimers(self, mock_uic_map_class: MagicMock) -> None:
        """Test place_order with blocking disclaimers."""
        mock_uic_map = MagicMock()
        mock_uic_map.get_uic.return_value = 21
        mock_uic_map_class.return_value = mock_uic_map
        
        client = SaxoClient(environment="sim")
        client.access_token = "mock-token"
        client.account_key = "mock-account"
        
        client.get_quote = MagicMock(return_value={
            "Quote": {
                "Ask": "151.25",
                "Bid": "151.23"
            }
        })
        
        client._precheck_order = MagicMock(side_effect=[
            {
                "PreCheckResult": "BlockingDisclaimers",
                "BlockingDisclaimers": [{"Id": "disclaimer-123"}]
            },
            {"PreCheckResult": "Accepted"}
        ])
        
        client._accept_disclaimer = MagicMock(return_value=True)
        
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"OrderId": "mock-order-123"}
            mock_post.return_value = mock_response
            mock_response.raise_for_status.return_value = None
            
            result = client.place_order("USDJPY", "Market", "Buy", Decimal("0.01"))
            
            client._accept_disclaimer.assert_called_once_with("disclaimer-123")
            
            assert client._precheck_order.call_count == 2
            
            assert result == {"OrderId": "mock-order-123"}

    @patch("src.utils.uic_map.UICMap")
    def test_place_order_with_guard_rejection(self, mock_uic_map_class: MagicMock) -> None:
        """Test place_order with guard rejection."""
        mock_uic_map = MagicMock()
        mock_uic_map.get_uic.return_value = 21
        mock_uic_map_class.return_value = mock_uic_map
        
        client = SaxoClient(environment="sim")
        client.access_token = "mock-token"
        client.account_key = "mock-account"
        
        client.get_quote = MagicMock(return_value={
            "Quote": {
                "Ask": "151.25",
                "Bid": "151.23"
            }
        })
        
        client._precheck_order = MagicMock(return_value={
            "KillSwitchRejection": True,
            "PreCheckResult": "Rejected"
        })
        
        with pytest.raises(OrderRejected) as excinfo:
            client.place_order("USDJPY", "Market", "Buy", Decimal("0.01"))
        
        assert "KillSwitch: Daily loss limit exceeded" in str(excinfo.value)
