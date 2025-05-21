"""
Advanced unit tests for SlippageGuard.
"""

import pytest

from src.core.guards.slippage_guard import SlippageGuard


class TestSlippageGuardAdvanced:
    """Advanced test cases for SlippageGuard."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.guard = SlippageGuard()

    def test_window_size_limit(self) -> None:
        """Test that slippage history is limited to window_size."""
        self.guard.window_size = 5

        for i in range(10):
            self.guard.add_slippage("EURUSD", 0.5 + i * 0.1)

        assert len(self.guard.slippage_history["EURUSD"]) == 5  # nosec: B101 # pytest assertion
        for val in self.guard.slippage_history["EURUSD"]:
            assert val >= 1.0 and val <= 1.4  # nosec: B101 # pytest assertion

    def test_multiple_instruments(self) -> None:
        """Test handling multiple instruments simultaneously."""
        instruments = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD"]

        for instrument in instruments:
            for i in range(15):  # Need at least 10 values for stats
                self.guard.add_slippage(instrument, 0.5 + i * 0.1)

        for instrument in instruments:
            assert instrument in self.guard.slippage_history  # nosec: B101 # pytest assertion
            assert (
                len(self.guard.slippage_history[instrument]) <= self.guard.window_size
            )  # nosec: B101 # pytest assertion

            mean, std = self.guard.get_slippage_stats(instrument)
            assert mean == pytest.approx(1.2, abs=0.5)  # nosec: B101 # pytest assertion
            assert std > 0.0  # nosec: B101 # pytest assertion

    def test_check_slippage_threshold_calculation(self) -> None:
        """Test the threshold calculation in check_slippage."""
        values = [0.4, 0.5, 0.6, 0.4, 0.5, 0.6]
        for val in values:
            self.guard.add_slippage("EURUSD", val)

        assert (
            self.guard.check_slippage("EURUSD", 1.1000, 1.1006) is True
        )  # nosec: B101 # pytest assertion

        assert (
            self.guard.check_slippage("EURUSD", 1.1000, 1.1007) is True
        )  # nosec: B101 # pytest assertion

        assert (
            self.guard.check_slippage("EURUSD", 1.1000, 1.1008) is False
        )  # nosec: B101 # pytest assertion

    def test_check_slippage_with_empty_history_fallback(self) -> None:
        """Test check_slippage with empty history uses fallback threshold."""

        assert (
            self.guard.check_slippage("NEWPAIR", 1.1000, 1.1006) is True
        )  # nosec: B101 # pytest assertion

        assert (
            self.guard.check_slippage("NEWPAIR", 1.1000, 1.1007) is True
        )  # nosec: B101 # pytest assertion

        assert (
            self.guard.check_slippage("NEWPAIR", 1.1000, 1.1008) is False
        )  # nosec: B101 # pytest assertion

    def test_check_slippage_with_insufficient_history(self) -> None:
        """Test check_slippage with insufficient history uses provisional values."""
        self.guard.add_slippage("EURUSD", 0.3)

        assert (
            self.guard.check_slippage("EURUSD", 1.1000, 1.1006) is True
        )  # nosec: B101 # pytest assertion

        assert (
            self.guard.check_slippage("EURUSD", 1.1000, 1.1007) is True
        )  # nosec: B101 # pytest assertion

        assert (
            self.guard.check_slippage("EURUSD", 1.1000, 1.1008) is False
        )  # nosec: B101 # pytest assertion
