"""
Unit tests for Prometheus metrics.
"""

from src.services.metrics.prometheus import update_trade_status, last_trade_status


def test_update_trade_status_filled() -> None:
    """Test update_trade_status with Filled status."""
    for status in ["Filled", "Executed"]:
        last_trade_status.labels(status=status).set(0)
    
    update_trade_status("Filled")
    
    assert last_trade_status.labels(status="Filled")._value.get() == 1
    assert last_trade_status.labels(status="Executed")._value.get() == 0


def test_update_trade_status_executed() -> None:
    """Test update_trade_status with Executed status."""
    for status in ["Filled", "Executed"]:
        last_trade_status.labels(status=status).set(0)
    
    update_trade_status("Executed")
    
    assert last_trade_status.labels(status="Filled")._value.get() == 0
    assert last_trade_status.labels(status="Executed")._value.get() == 1


def test_update_trade_status_invalid() -> None:
    """Test update_trade_status with invalid status."""
    for status in ["Filled", "Executed"]:
        last_trade_status.labels(status=status).set(0)
    
    update_trade_status("Invalid")
    
    assert last_trade_status.labels(status="Filled")._value.get() == 0
    assert last_trade_status.labels(status="Executed")._value.get() == 0
