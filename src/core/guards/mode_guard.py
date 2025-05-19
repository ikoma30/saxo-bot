"""
ModeGuard module.

This module provides the ModeGuard class for monitoring and controlling mode transitions.
"""

import logging
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("saxo")


class TradingMode(Enum):
    """Trading mode enum for HV/LV modes."""

    HV_HL = "HV_HL"  # High volatility, high liquidity
    HV_LL = "HV_LL"  # High volatility, low liquidity
    LV_HL = "LV_HL"  # Low volatility, high liquidity
    LV_LL = "LV_LL"  # Low volatility, low liquidity


@dataclass
class ModeTransition:
    """Mode transition with timestamp."""

    from_mode: TradingMode
    to_mode: TradingMode
    timestamp: float


class ModeGuard:
    """Monitor and control trading mode transitions."""

    def __init__(self, transition_limit: int = 3, time_window_seconds: int = 900) -> None:
        """
        Initialize the ModeGuard.

        Args:
            transition_limit: Maximum number of mode transitions allowed in time window
            time_window_seconds: Time window in seconds to monitor transitions
        """
        self.transition_limit = transition_limit
        self.time_window_seconds = time_window_seconds
        self.transitions: deque[ModeTransition] = deque()
        self.current_mode: TradingMode = TradingMode.LV_LL  # Default to safest mode
        self.pause_until: float = 0

    def transition_mode(self, new_mode: TradingMode) -> bool:
        """
        Register a mode transition and check if it triggers the ModeGuard.

        As per specification:
        ModeGuard: Shift from HV to LV 3 or more times within 15 minutes → Pause (15 min)

        Args:
            new_mode: The new trading mode

        Returns:
            bool: True if transition is allowed, False if ModeGuard is triggered
        """
        now = time.time()

        if now < self.pause_until:
            logger.warning(
                f"ModeGuard is active: trading paused for "
                f"{int(self.pause_until - now)} more seconds"
            )
            return False

        if self.current_mode == new_mode:
            return True

        transition = ModeTransition(from_mode=self.current_mode, to_mode=new_mode, timestamp=now)
        self.transitions.append(transition)

        window_start = now - self.time_window_seconds
        while self.transitions and self.transitions[0].timestamp < window_start:
            self.transitions.popleft()

        hv_to_lv_count = sum(
            1
            for t in self.transitions
            if (
                t.from_mode in (TradingMode.HV_HL, TradingMode.HV_LL)
                and t.to_mode in (TradingMode.LV_HL, TradingMode.LV_LL)
            )
        )

        self.current_mode = new_mode

        if hv_to_lv_count >= self.transition_limit:
            logger.warning(
                f"ModeGuard triggered: {hv_to_lv_count} HV→LV transitions in "
                f"{self.time_window_seconds} seconds"
            )
            self.pause_until = now + 900  # Pause for 15 minutes (900 seconds)
            return False

        logger.info(f"Mode transition: {transition.from_mode.value} → {transition.to_mode.value}")
        return True

    def is_paused(self) -> bool:
        """Check if trading is currently paused by ModeGuard."""
        return time.time() < self.pause_until

    def get_current_mode(self) -> TradingMode:
        """Get the current trading mode."""
        return self.current_mode
