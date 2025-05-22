"""
Unit tests for Prometheus metrics.
"""

from src.services.metrics.prometheus import (
    update_trade_status,
    record_order_poll_time,
    last_trade_status,
    order_poll_seconds,
)


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


def test_record_order_poll_time() -> None:
    """Test record_order_poll_time function."""
    for status in ["Filled", "Executed", "Timeout"]:
        order_poll_seconds.labels(status=status).observe(0)

    record_order_poll_time("Filled", 1.5)
    record_order_poll_time("Executed", 2.5)
    record_order_poll_time("Timeout", 3.5)

    assert order_poll_seconds._labelnames == ("status",)
