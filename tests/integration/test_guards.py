"""
Integration tests for guard systems.

Tests SlippageGuard, ModeGuard, KillSwitch, LatencyGuard, and PriorityGuard.
"""

import logging
import os

import pytest

from src.core.guards.kill_switch import KillSwitch
from src.core.guards.latency_guard import LatencyGuard
from src.core.guards.mode_guard import ModeGuard, TradingMode
from src.core.guards.priority_guard import BotPriority, BotState, PriorityGuard
from src.core.saxo_client import SaxoClient

logger = logging.getLogger("test")


@pytest.mark.integration
def test_slippage_guard_integration() -> None:
    """Test SlippageGuard integration with SaxoClient."""
    if "CI" in os.environ and not os.environ.get("SIM_REFRESH_TOKEN"):
        pytest.skip("Skipping in CI without SIM_REFRESH_TOKEN")
    
    client = SaxoClient(environment="sim")
    result = client.authenticate()
    
    if not result: 
        pytest.skip("Authentication failed, skipping guard test")
    
    instrument = "USDJPY"
    
    quote = client.get_quote(instrument)
    assert quote is not None  # nosec: B101 # pytest assertion
    
    mid_price = (quote["Ask"] + quote["Bid"]) / 2
    
    fill_price = mid_price + 0.1  # Small slippage
    result = client.slippage_guard.check_slippage(instrument, mid_price, fill_price)
    assert result is True  # nosec: B101 # pytest assertion
    
    fill_price = mid_price + 10.0  # Large slippage
    result = client.slippage_guard.check_slippage(instrument, mid_price, fill_price)
    assert result is False  # nosec: B101 # pytest assertion


@pytest.mark.integration
def test_mode_guard_integration() -> None:
    """Test ModeGuard integration."""
    mode_guard = ModeGuard(transition_limit=3, time_window_seconds=15)
    
    result = mode_guard.transition_mode(TradingMode.HV_HL)
    assert result is True  # nosec: B101 # pytest assertion
    assert mode_guard.get_current_mode() == TradingMode.HV_HL  # nosec: B101 # pytest assertion
    
    result = mode_guard.transition_mode(TradingMode.HV_HL)
    assert result is True  # nosec: B101 # pytest assertion
    
    result = mode_guard.transition_mode(TradingMode.LV_HL)
    assert result is True  # nosec: B101 # pytest assertion
    
    result = mode_guard.transition_mode(TradingMode.HV_HL)
    assert result is True  # nosec: B101 # pytest assertion
    
    result = mode_guard.transition_mode(TradingMode.LV_HL)
    assert result is True  # nosec: B101 # pytest assertion
    
    result = mode_guard.transition_mode(TradingMode.HV_HL)
    assert result is True  # nosec: B101 # pytest assertion
    
    result = mode_guard.transition_mode(TradingMode.LV_HL)
    assert result is False  # nosec: B101 # pytest assertion
    assert mode_guard.is_paused() is True  # nosec: B101 # pytest assertion


@pytest.mark.integration
def test_kill_switch_integration() -> None:
    """Test KillSwitch integration."""
    kill_switch = KillSwitch(daily_loss_threshold_pct=-1.5, suspension_hours=24)
    
    initial_equity = 800000.0  # 800,000 JPY
    kill_switch.set_initial_equity(initial_equity)
    
    current_equity = 795000.0  # -0.625% loss
    result = kill_switch.check_equity(current_equity)
    assert result is True  # nosec: B101 # pytest assertion
    assert kill_switch.is_active() is False  # nosec: B101 # pytest assertion
    
    current_equity = 785000.0  # -1.875% loss
    result = kill_switch.check_equity(current_equity)
    assert result is False  # nosec: B101 # pytest assertion
    assert kill_switch.is_active() is True  # nosec: B101 # pytest assertion


@pytest.mark.integration
def test_latency_guard_integration() -> None:
    """Test LatencyGuard integration."""
    latency_guard = LatencyGuard(threshold_ms=12.0, consecutive_limit=5)
    
    for _ in range(4):
        result = latency_guard.check_latency(10.0)
        assert result is True  # nosec: B101 # pytest assertion
    
    result = latency_guard.check_latency(15.0)
    assert result is True  # nosec: B101 # pytest assertion
    
    latency_guard.reset()
    
    for _ in range(5):
        result = latency_guard.check_latency(15.0)
    
    assert result is False  # nosec: B101 # pytest assertion
    assert latency_guard.is_triggered() is True  # nosec: B101 # pytest assertion


@pytest.mark.integration
def test_priority_guard_integration() -> None:
    """Test PriorityGuard integration."""
    priority_guard = PriorityGuard()
    
    priority_guard.register_bot("micro_rev", BotPriority.HIGH)
    priority_guard.register_bot("main", BotPriority.NORMAL)
    priority_guard.register_bot("test", BotPriority.LOW)
    
    priority_guard.update_bot_state("micro_rev", BotState.RUNNING)
    priority_guard.update_bot_state("main", BotState.RUNNING)
    priority_guard.update_bot_state("test", BotState.RUNNING)
    
    assert priority_guard.get_bot_state("micro_rev") == BotState.RUNNING  # nosec: B101 # pytest assertion
    assert priority_guard.get_bot_state("main") == BotState.PAUSED  # nosec: B101 # pytest assertion
    assert priority_guard.get_bot_state("test") == BotState.PAUSED  # nosec: B101 # pytest assertion
    
    priority_guard.update_bot_state("micro_rev", BotState.STOPPED)
    
    priority_guard.update_bot_state("main", BotState.RUNNING)
    priority_guard.update_bot_state("test", BotState.RUNNING)
    
    assert priority_guard.get_bot_state("micro_rev") == BotState.STOPPED  # nosec: B101 # pytest assertion
    assert priority_guard.get_bot_state("main") == BotState.RUNNING  # nosec: B101 # pytest assertion
    assert priority_guard.get_bot_state("test") == BotState.PAUSED  # nosec: B101 # pytest assertion
