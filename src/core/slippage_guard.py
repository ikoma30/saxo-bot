"""
SlippageGuard module.

This module provides the SlippageGuard class for monitoring and controlling slippage.
"""

import logging
import statistics
from collections import deque

logger = logging.getLogger("saxo")


class SlippageGuard:
    """Monitor and control slippage for trading operations."""

    def __init__(self, window_size: int = 2000) -> None:
        """
        Initialize the SlippageGuard.

        Args:
            window_size: Size of the rolling window for slippage statistics (default: 2000)
        """
        self.window_size = window_size
        self.slippage_history: dict[str, deque[float]] = {}
        self.provisional_mean = 0.0  # pip
        self.provisional_std = 0.2  # pip
        
    def add_slippage(self, instrument: str, slippage_pip: float) -> None:
        """
        Add a slippage value to the history for an instrument.

        Args:
            instrument: The instrument identifier (e.g., "EURUSD")
            slippage_pip: The slippage value in pips
        """
        if instrument not in self.slippage_history:
            self.slippage_history[instrument] = deque(maxlen=self.window_size)
        
        self.slippage_history[instrument].append(slippage_pip)
        logger.info(f"Added slippage {slippage_pip} pip for {instrument}")
    
    def get_slippage_stats(self, instrument: str) -> tuple[float, float]:
        """
        Get mean and standard deviation of slippage for an instrument.

        Args:
            instrument: The instrument identifier (e.g., "EURUSD")

        Returns:
            Tuple[float, float]: (mean, standard deviation) of slippage in pips
        """
        if instrument not in self.slippage_history or not self.slippage_history[instrument]:
            logger.info(f"No slippage history for {instrument}, using provisional values")
            return self.provisional_mean, self.provisional_std
        
        data = list(self.slippage_history[instrument])
        if len(data) < 10:  # Require at least 10 data points for meaningful statistics
            logger.info(f"Insufficient slippage history for {instrument}, using provisional values")
            return self.provisional_mean, self.provisional_std
        
        mean = statistics.mean(data)
        std = statistics.stdev(data) if len(data) > 1 else 0.0
        
        logger.info(f"Slippage stats for {instrument}: mean={mean:.4f}, std={std:.4f}")
        return mean, std
    
    def check_slippage(self, instrument: str, quote_mid: float, fill_price: float) -> bool:
        """
        Check if slippage exceeds the allowed threshold.

        As per specification:
        Fill - QuoteMid > max(μ_slip + 1.5 σ_slip, 0.7 pip) → Reject order

        Args:
            instrument: The instrument identifier (e.g., "EURUSD")
            quote_mid: The mid-price of the quote
            fill_price: The fill price

        Returns:
            bool: True if slippage is acceptable, False if it exceeds threshold
        """
        slippage_pip = abs(fill_price - quote_mid) * 1000
        
        mean, std = self.get_slippage_stats(instrument)
        threshold = max(mean + 1.5 * std, 0.7)
        
        logger.info(
            f"Checking slippage for {instrument}: {slippage_pip:.4f} pip "
            f"against threshold {threshold:.4f} pip"
        )
        
        if slippage_pip > threshold:
            logger.warning(
                f"Excessive slippage detected for {instrument}: {slippage_pip:.4f} pip "
                f"exceeds threshold {threshold:.4f} pip"
            )
            return False
        
        return True
