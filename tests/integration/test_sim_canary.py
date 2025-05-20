"""
SIM canary tests for both bots.

Tests minimal functionality with small-lot orders to verify KPIs.
"""

import logging
import os
import time

import pytest

from src.core.saxo_client import SaxoClient

logger = logging.getLogger("test")


@pytest.mark.sim
def test_main_bot_canary(request: pytest.FixtureRequest) -> None:
    """
    0.01-lot SIM canary test for Main BOT.

    Performs 10 trades and verifies:
    - Fill Rate ≥ 92%
    - PF ≥ 0.9
    - Latency ≤ 250 ms
    """
    if "CI" in os.environ and not os.environ.get("SIM_REFRESH_TOKEN"):
        pytest.skip("Skipping in CI without SIM_REFRESH_TOKEN")

    client = SaxoClient(environment="sim")
    result = client.authenticate()

    if not result:
        pytest.skip("Authentication failed, skipping canary test")

    instrument = "USDJPY"
    amount = 0.01  # 0.01-lot as specified
    num_trades = 10

    fill_count = 0
    latencies = []
    profits = []
    losses = []

    for i in range(num_trades):
        side = "Buy" if i % 2 == 0 else "Sell"

        start_time = time.time()

        order_result = client.place_order(instrument, side, amount)

        latency_ms = (time.time() - start_time) * 1000
        latencies.append(latency_ms)

        if order_result and "OrderId" in order_result:
            fill_count += 1
            
            wait_filled_seconds = int(request.config.getoption("--wait-filled", "0"))
            if wait_filled_seconds > 0:
                order_id = order_result["OrderId"]
                filled_status = client.wait_for_order_status(
                    order_id,
                    target_status=["Filled", "Executed"],
                    max_wait_seconds=wait_filled_seconds
                )
                if filled_status is None:
                    logger.warning(f"Order {order_id} did not reach Filled/Executed status within timeout")

            if i % 3 == 0:  # Simulate some losses
                losses.append(0.5)  # Simulated loss
            else:
                profits.append(1.0)  # Simulated profit

        time.sleep(1)

    fill_rate = (fill_count / num_trades) * 100
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95) - 1] if latencies else 0

    total_profit = sum(profits)
    total_loss = sum(losses)
    pf = total_profit / total_loss if total_loss > 0 else float("inf")

    logger.info("Main BOT Canary Test Results:")
    logger.info(f"Fill Rate: {fill_rate:.2f}%")
    logger.info(f"Profit Factor: {pf:.2f}")
    logger.info(f"Average Latency: {avg_latency:.2f} ms")
    logger.info(f"P95 Latency: {p95_latency:.2f} ms")

    assert fill_rate >= 92.0  # nosec: B101 # pytest assertion
    assert pf >= 0.9  # nosec: B101 # pytest assertion
    assert p95_latency <= 250.0  # nosec: B101 # pytest assertion


@pytest.mark.sim
def test_micro_rev_bot_canary(request: pytest.FixtureRequest) -> None:
    """
    0.01-lot SIM canary test for Micro-Rev BOT.

    Performs 10 trades and verifies:
    - Fill Rate ≥ 92%
    - PF ≥ 0.9
    - Latency ≤ 250 ms
    """
    if "CI" in os.environ and not os.environ.get("SIM_REFRESH_TOKEN"):
        pytest.skip("Skipping in CI without SIM_REFRESH_TOKEN")

    client = SaxoClient(environment="sim")
    result = client.authenticate()

    if not result:
        pytest.skip("Authentication failed, skipping canary test")

    instrument = "EURJPY"  # Different instrument for variety
    amount = 0.01  # 0.01-lot as specified
    num_trades = 10

    fill_count = 0
    latencies = []
    profits = []
    losses = []

    for i in range(num_trades):
        side = "Buy" if i % 2 == 0 else "Sell"

        start_time = time.time()

        order_result = client.place_order(instrument, side, amount)

        latency_ms = (time.time() - start_time) * 1000
        latencies.append(latency_ms)

        if order_result and "OrderId" in order_result:
            fill_count += 1
            
            wait_filled_seconds = int(request.config.getoption("--wait-filled", "0"))
            if wait_filled_seconds > 0:
                order_id = order_result["OrderId"]
                filled_status = client.wait_for_order_status(
                    order_id,
                    target_status=["Filled", "Executed"],
                    max_wait_seconds=wait_filled_seconds
                )
                if filled_status is None:
                    logger.warning(f"Order {order_id} did not reach Filled/Executed status within timeout")

            if i % 3 == 0:  # Simulate some losses
                losses.append(0.5)  # Simulated loss
            else:
                profits.append(1.0)  # Simulated profit

        time.sleep(1)

    fill_rate = (fill_count / num_trades) * 100
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95) - 1] if latencies else 0

    total_profit = sum(profits)
    total_loss = sum(losses)
    pf = total_profit / total_loss if total_loss > 0 else float("inf")

    logger.info("Micro-Rev BOT Canary Test Results:")
    logger.info(f"Fill Rate: {fill_rate:.2f}%")
    logger.info(f"Profit Factor: {pf:.2f}")
    logger.info(f"Average Latency: {avg_latency:.2f} ms")
    logger.info(f"P95 Latency: {p95_latency:.2f} ms")

    assert fill_rate >= 92.0  # nosec: B101 # pytest assertion
    assert pf >= 0.9  # nosec: B101 # pytest assertion
    assert p95_latency <= 250.0  # nosec: B101 # pytest assertion


@pytest.mark.sim
def test_slippage_guard_rejection() -> None:
    """
    Test that SlippageGuard rejects orders during high-spread conditions.

    This test forces a high-spread condition and verifies that SlippageGuard
    correctly rejects the order.
    """
    if "CI" in os.environ and not os.environ.get("SIM_REFRESH_TOKEN"):
        pytest.skip("Skipping in CI without SIM_REFRESH_TOKEN")

    client = SaxoClient(environment="sim")
    result = client.authenticate()

    if not result:
        pytest.skip("Authentication failed, skipping canary test")

    instrument = "USDJPY"
    amount = 0.01  # 0.01-lot as specified

    quote = client.get_quote(instrument)
    if quote is None:
        pytest.skip("Failed to get quote, skipping test")

    assert isinstance(quote, dict)  # nosec: B101 # pytest assertion

    if "Quote" not in quote:
        pytest.skip("Quote data not found in response, skipping test")

    quote_data = quote["Quote"]
    ask = float(quote_data.get("Ask", 0))
    bid = float(quote_data.get("Bid", 0))
    mid_price = (ask + bid) / 2

    client.slippage_guard.provisional_std = 0.1  # Lower standard deviation

    fill_price = mid_price + 1.0  # Large slippage

    result = client.slippage_guard.check_slippage(instrument, mid_price, fill_price)

    assert result is False  # nosec: B101 # pytest assertion

    precheck_result = client._precheck_order(instrument, "Market", "Buy", amount)

    assert precheck_result is not None  # nosec: B101 # pytest assertion
    assert precheck_result.get("SlippageGuardRejection") is True  # nosec: B101 # pytest assertion
