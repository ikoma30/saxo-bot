"""
LatencyGuard module.

This module provides the LatencyGuard class for monitoring and controlling API latency.
"""

import logging
from collections import deque

logger = logging.getLogger("saxo")


class LatencyGuard:
    """Monitor and control API latency."""

    def __init__(self, threshold_ms: float = 12.0, consecutive_limit: int = 5) -> None:
        """
        Initialize the LatencyGuard.

        Args:
            threshold_ms: Latency threshold in milliseconds
            consecutive_limit: Number of consecutive high latency events before triggering
        """
        self.threshold_ms = threshold_ms
        self.consecutive_limit = consecutive_limit
        self.latency_history: deque[float] = deque(maxlen=consecutive_limit)
        self.triggered = False

    def check_latency(self, latency_ms: float) -> bool:
        """
        Check if the current latency triggers the LatencyGuard.

        As per specification:
        Latency Guard: 5 consecutive round-trip delays > 12 ms → fail-safe to LV-LL

        Args:
            latency_ms: Measured latency in milliseconds

        Returns:
            bool: True if latency is acceptable, False if LatencyGuard is triggered
        """
        self.latency_history.append(latency_ms)

        if len(self.latency_history) < self.consecutive_limit:
            return True

        high_latency = all(lat > self.threshold_ms for lat in self.latency_history)

        if high_latency and not self.triggered:
            logger.warning(
                f"LatencyGuard triggered: {self.consecutive_limit} consecutive latencies "
                f"exceed {self.threshold_ms} ms threshold"
            )
            self.triggered = True
            return False

        if not high_latency and self.triggered:
            logger.info("LatencyGuard: Latency returned to normal levels")
            self.triggered = False

        return not self.triggered

    def is_triggered(self) -> bool:
        """Check if LatencyGuard is currently triggered."""
        return self.triggered

    def reset(self) -> None:
        """Reset the LatencyGuard status."""
        self.latency_history.clear()
        self.triggered = False
        logger.info("LatencyGuard reset")
