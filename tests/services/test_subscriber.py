"""
Tests for the Subscriber service.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import sqlite3

from src.services.subscriber.main import (
    create_tables,
    process_activity,
    process_trade,
    healthz,
    metrics,
    get_trades,
)


class TestSubscriberService:
    """Tests for the Subscriber service."""

    def test_create_tables(self) -> None:
        """Test database table creation."""
        mock_conn = MagicMock(spec=sqlite3.Connection)
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        with patch("src.services.subscriber.main.db_conn", mock_conn):
            create_tables()
        
        assert mock_cursor.execute.call_count == 2
        mock_conn.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_activity(self) -> None:
        """Test processing an activity message."""
        mock_conn = MagicMock(spec=sqlite3.Connection)
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        activity_data = {
            "ReferenceId": "activities-subscription",
            "Data": {
                "ActivityId": "act-123",
                "ActivityType": "OrderFill",
                "Timestamp": "2025-05-19T12:00:00Z",
                "Instrument": {"Symbol": "USDJPY"},
                "Description": "Order filled"
            }
        }
        
        with patch("src.services.subscriber.main.db_conn", mock_conn):
            with patch("src.services.subscriber.main.ACTIVITY_COUNT") as mock_counter:
                await process_activity(activity_data)
        
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        
        mock_counter.labels.assert_called_once()
        mock_counter.labels().inc.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_trade(self) -> None:
        """Test processing a trade message."""
        mock_conn = MagicMock(spec=sqlite3.Connection)
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        trade_data = {
            "ReferenceId": "trades-subscription",
            "Data": {
                "OrderId": "order-123",
                "Instrument": {"Symbol": "USDJPY"},
                "BuySell": "Buy",
                "Amount": "1000",
                "Price": "151.25",
                "Timestamp": "2025-05-19T12:00:00Z",
                "ProfitLoss": {"Amount": "100"}
            }
        }
        
        with patch("src.services.subscriber.main.db_conn", mock_conn):
            with patch("src.services.subscriber.main.TRADE_FILLS") as mock_counter:
                await process_trade(trade_data)
        
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        
        mock_counter.labels.assert_called_once()
        mock_counter.labels().inc.assert_called_once()

    @pytest.mark.asyncio
    async def test_healthz_endpoint_healthy(self) -> None:
        """Test healthz endpoint when service is healthy."""
        with patch("src.services.subscriber.main.is_healthy", True):
            response = await healthz()
            assert response.status_code == 200
            assert response.body == b'{"status":"ok"}'

    @pytest.mark.asyncio
    async def test_healthz_endpoint_unhealthy(self) -> None:
        """Test healthz endpoint when service is unhealthy."""
        with patch("src.services.subscriber.main.is_healthy", False):
            response = await healthz()
            assert response.status_code == 503
            assert response.body == b'{"status":"error"}'

    @pytest.mark.asyncio
    async def test_get_trades_endpoint(self) -> None:
        """Test get_trades endpoint."""
        mock_conn = MagicMock(spec=sqlite3.Connection)
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        mock_cursor.fetchall.return_value = [
            ("order-123", "USDJPY", "Buy", 0.01, 151.25, "2025-05-19T12:00:00Z", 100.0)
        ]
        
        with patch("src.services.subscriber.main.db_conn", mock_conn):
            result = await get_trades()
        
        mock_cursor.execute.assert_called_once()
        
        assert len(result) == 1
        assert result[0].order_id == "order-123"
        assert result[0].instrument == "USDJPY"
        assert result[0].side == "Buy"
        assert result[0].amount == 0.01
        assert result[0].fill_price == 151.25
        assert result[0].fill_time == "2025-05-19T12:00:00Z"
        assert result[0].profit_loss == 100.0
