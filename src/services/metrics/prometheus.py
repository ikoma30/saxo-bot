"""
Prometheus metrics for Saxo Bot.
"""

import logging
from prometheus_client import Gauge, Summary

logger = logging.getLogger(__name__)

last_trade_status = Gauge(
    "last_trade_status", "Status of the last trade (1=success, 0=failure)", ["status"]
)

order_poll_seconds = Summary(
    "order_poll_seconds", "Time spent polling for order status in seconds", ["status"]
)


def update_trade_status(status: str) -> None:
    """
    Update the trade status metric.

    Args:
        status: The status of the trade (Filled or Executed)
    """
    logger.info(f"Updating trade status metric: {status}")

    for s in ["Filled", "Executed"]:
        last_trade_status.labels(status=s).set(0)

    if status in ["Filled", "Executed"]:
        last_trade_status.labels(status=status).set(1)
        logger.info(f"Trade status metric set to {status}=1")


def record_order_poll_time(status: str, seconds: float) -> None:
    """
    Record the time spent polling for order status.

    Args:
        status: The final status of the order (Filled, Executed, Timeout)
        seconds: The time spent polling in seconds
    """
    logger.info(f"Recording order poll time: {seconds:.2f}s with status {status}")
    order_poll_seconds.labels(status=status).observe(seconds)
