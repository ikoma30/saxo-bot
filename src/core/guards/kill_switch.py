"""
KillSwitch module.

This module provides the KillSwitch class for monitoring and controlling daily loss limits.
"""

import logging
import time

logger = logging.getLogger("saxo")


class KillSwitch:
    """Monitor and control daily loss limits."""
    
    def __init__(self, daily_loss_threshold_pct: float = -1.5, suspension_hours: int = 24) -> None:
        """
        Initialize the KillSwitch.
        
        Args:
            daily_loss_threshold_pct: Daily loss threshold percentage (negative value)
            suspension_hours: Trading suspension duration in hours when threshold is exceeded
        """
        self.daily_loss_threshold_pct = daily_loss_threshold_pct
        self.suspension_seconds = suspension_hours * 3600
        self.initial_equity = 0.0
        self.activated_until = 0.0
    
    def set_initial_equity(self, equity: float) -> None:
        """
        Set the initial equity value for the day.
        
        Args:
            equity: Equity value in JPY
        """
        self.initial_equity = equity
        logger.info(f"KillSwitch: Initial equity set to {equity:.2f} JPY")
    
    def check_equity(self, current_equity: float) -> bool:
        """
        Check if the current equity triggers the KillSwitch.
        
        As per specification:
        Kill-Switch: When daily loss reaches -1.5%, all positions are closed immediately
        and new positions are stopped for 24 hours.
        
        Args:
            current_equity: Current equity value in JPY
        
        Returns:
            bool: True if trading can continue, False if KillSwitch is triggered
        """
        if self.initial_equity <= 0:
            logger.warning("KillSwitch: Initial equity not set, skipping check")
            return True
        
        now = time.time()
        
        if now < self.activated_until:
            logger.warning(
                f"KillSwitch active: trading suspended for "
                f"{int((self.activated_until - now) / 3600)} more hours"
            )
            return False
        
        daily_pnl_pct = ((current_equity - self.initial_equity) / self.initial_equity) * 100
        
        if daily_pnl_pct <= self.daily_loss_threshold_pct:
            logger.error(
                f"KillSwitch triggered: Daily loss {daily_pnl_pct:.2f}% exceeds threshold "
                f"{self.daily_loss_threshold_pct:.2f}%"
            )
            self.activated_until = now + self.suspension_seconds
            return False
        
        return True
    
    def is_active(self) -> bool:
        """Check if KillSwitch is currently active."""
        return time.time() < self.activated_until
    
    def reset(self) -> None:
        """Reset the KillSwitch status."""
        self.activated_until = 0
        logger.info("KillSwitch reset")
