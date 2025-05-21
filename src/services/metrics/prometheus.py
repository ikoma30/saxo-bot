"""
Prometheus metrics for Saxo Bot.
"""

import logging
from prometheus_client import Gauge

logger = logging.getLogger(__name__)

last_trade_status = Gauge(
    "last_trade_status", "Status of the last trade (1=success, 0=failure)", ["status"]
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
