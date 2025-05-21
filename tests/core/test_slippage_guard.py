"""
Unit tests for the SlippageGuard class.
"""

import pytest
from src.core.slippage_guard import SlippageGuard


class TestSlippageGuard:
    """Test suite for the SlippageGuard class."""

    def setup_method(self) -> None:
        """Set up test environment before each test method."""
        self.guard = SlippageGuard()

    def test_init(self) -> None:
        """Test guard initialization."""
        assert self.guard.window_size == 2000  # nosec: B101 # pytest assertion
        assert self.guard.slippage_history == {}  # nosec: B101 # pytest assertion
        assert self.guard.provisional_mean == 0.0  # nosec: B101 # pytest assertion
        assert self.guard.provisional_std == 0.2  # nosec: B101 # pytest assertion

    def test_init_custom_window(self) -> None:
        """Test guard initialization with custom window size."""
        guard = SlippageGuard(window_size=1000)
        assert guard.window_size == 1000  # nosec: B101 # pytest assertion
        assert guard.slippage_history == {}  # nosec: B101 # pytest assertion

    def test_add_slippage(self) -> None:
        """Test adding slippage values."""
        self.guard.add_slippage("EURUSD", 0.5)
        assert "EURUSD" in self.guard.slippage_history  # nosec: B101 # pytest assertion
        assert len(self.guard.slippage_history["EURUSD"]) == 1  # nosec: B101 # pytest assertion
        assert self.guard.slippage_history["EURUSD"][0] == 0.5  # nosec: B101 # pytest assertion

    def test_add_slippage_multiple(self) -> None:
        """Test adding multiple slippage values."""
        self.guard.add_slippage("EURUSD", 0.5)
        self.guard.add_slippage("EURUSD", 0.6)
        self.guard.add_slippage("USDJPY", 0.7)

        assert "EURUSD" in self.guard.slippage_history  # nosec: B101 # pytest assertion
        assert "USDJPY" in self.guard.slippage_history  # nosec: B101 # pytest assertion
        assert len(self.guard.slippage_history["EURUSD"]) == 2  # nosec: B101 # pytest assertion
        assert len(self.guard.slippage_history["USDJPY"]) == 1  # nosec: B101 # pytest assertion

    def test_get_slippage_stats_empty(self) -> None:
        """Test getting stats for instrument with no history."""
        mean, std = self.guard.get_slippage_stats("EURUSD")
        assert mean == self.guard.provisional_mean  # nosec: B101 # pytest assertion
        assert std == self.guard.provisional_std  # nosec: B101 # pytest assertion

    def test_get_slippage_stats_insufficient(self) -> None:
        """Test getting stats for instrument with insufficient history."""
        self.guard.add_slippage("EURUSD", 0.5)
        self.guard.add_slippage("EURUSD", 0.6)
        mean, std = self.guard.get_slippage_stats("EURUSD")
        assert mean == self.guard.provisional_mean  # nosec: B101 # pytest assertion
        assert std == self.guard.provisional_std  # nosec: B101 # pytest assertion

    def test_get_slippage_stats_sufficient(self) -> None:
        """Test getting stats for instrument with sufficient history."""
        for _ in range(15):
            self.guard.add_slippage("EURUSD", 0.5)
        mean, std = self.guard.get_slippage_stats("EURUSD")
        assert mean == 0.5  # nosec: B101 # pytest assertion
        assert std == 0.0  # nosec: B101 # pytest assertion

    def test_get_slippage_stats_with_variance(self) -> None:
        """Test getting stats for instrument with variance in history."""
        values = [0.4, 0.5, 0.6, 0.5, 0.4, 0.5, 0.6, 0.5, 0.4, 0.5]
        for val in values:
            self.guard.add_slippage("EURUSD", val)
        
        mean, std = self.guard.get_slippage_stats("EURUSD")
        assert mean == pytest.approx(0.49, abs=0.01)  # nosec: B101 # pytest assertion
        assert std > 0.0  # nosec: B101 # pytest assertion

    def test_check_slippage_acceptable(self) -> None:
        """Test checking acceptable slippage."""
        for _ in range(15):
            self.guard.add_slippage("EURUSD", 0.5)

        result = self.guard.check_slippage("EURUSD", 1.1230, 1.1234)
        assert result is True  # nosec: B101 # pytest assertion

    def test_check_slippage_excessive(self) -> None:
        """Test checking excessive slippage."""
        for _ in range(15):
            self.guard.add_slippage("EURUSD", 0.5)

        result = self.guard.check_slippage("EURUSD", 1.1230, 1.1240)
        assert result is False  # nosec: B101 # pytest assertion

    def test_check_slippage_no_history(self) -> None:
        """Test checking slippage with no history."""
        result = self.guard.check_slippage("EURUSD", 1.1230, 1.1240)
        assert result is False  # nosec: B101 # pytest assertion

        result = self.guard.check_slippage("EURUSD", 1.1230, 1.1236)
        assert result is True  # nosec: B101 # pytest assertion

    def test_check_slippage_edge_cases(self) -> None:
        """Test checking slippage with edge cases."""
        for _ in range(15):
            self.guard.add_slippage("EURUSD", 0.5)

        result = self.guard.check_slippage("EURUSD", 1.1230, 1.1230)
        assert result is True  # nosec: B101 # pytest assertion

        result = self.guard.check_slippage("EURUSD", 1.1230, 1.2230)
        assert result is False  # nosec: B101 # pytest assertion

        mean, std = self.guard.get_slippage_stats("EURUSD")
        threshold = max(mean + 1.5 * std, 0.7)
        exact_slippage = threshold / 1000
        result = self.guard.check_slippage("EURUSD", 1.1230, 1.1230 + exact_slippage)
        assert result is True  # nosec: B101 # pytest assertion
