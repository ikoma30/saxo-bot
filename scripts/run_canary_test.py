#!/usr/bin/env python3
"""
Run a canary test with small lot sizes to verify trading functionality.

This script executes a specified number of trades with minimal lot size (0.01)
to validate the trading system in the simulation environment.
"""

import logging
import sys
import time
from decimal import Decimal
from pathlib import Path

from src.core.saxo_client import SaxoClient

sys.path.append(str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("canary")

DEFAULT_INSTRUMENT = "USDJPY"
DEFAULT_TRADES = 10
DEFAULT_LOT_SIZE = 0.01
DEFAULT_INTERVAL = 5  # seconds between trades


def run_canary_test(
    instrument: str = DEFAULT_INSTRUMENT,
    num_trades: int = DEFAULT_TRADES,
    lot_size: float = DEFAULT_LOT_SIZE,
    interval: int = DEFAULT_INTERVAL,
) -> tuple[float, float, list[dict]]:
    """
    Run a canary test with small trades.

    Args:
        instrument: The trading instrument (default: USDJPY)
        num_trades: Number of trades to execute (default: 10)
        lot_size: Lot size for trades (default: 0.01)
        interval: Time between trades in seconds (default: 5)

    Returns:
        Tuple[float, float, List[dict]]: (fill_rate, performance_factor, orders_data)
    """
    client = SaxoClient(environment="sim")

    if not client.authenticate():
        logger.error("Authentication failed, cannot run canary test")
        return 0.0, 0.0, []

    orders_placed = 0
    orders_filled = 0
    orders_data: list[dict] = []
    latencies: list[float] = []

    logger.info(f"Starting canary test: {num_trades} trades of {lot_size} lots for {instrument}")

    for i in range(num_trades):
        side = "Buy" if i % 2 == 0 else "Sell"

        start_time = time.time()

        quote_data = client.get_quote(instrument)
        if not quote_data or "Quote" not in quote_data:
            logger.error(f"Failed to get quote for trade {i+1}")
            time.sleep(interval)
            continue

        quote = quote_data["Quote"]
        pre_ask = float(quote.get("Ask", 0))
        pre_bid = float(quote.get("Bid", 0))
        pre_mid = (pre_ask + pre_bid) / 2

        logger.info(f"Placing {side} order {i+1}/{num_trades} for {lot_size} lots of {instrument}")
        order_result = client.place_order(
            instrument=instrument,
            order_type="Market",
            side=side,
            amount=Decimal(str(lot_size)),
        )

        latency_ms = (time.time() - start_time) * 1000
        latencies.append(latency_ms)

        if not order_result:
            logger.error(f"Failed to place order {i+1}/{num_trades}")
            time.sleep(interval)
            continue

        orders_placed += 1

        if "OrderId" in order_result:
            orders_filled += 1
            order_id = order_result["OrderId"]

            post_quote_data = client.get_quote(instrument)
            if post_quote_data and "Quote" in post_quote_data:
                post_quote = post_quote_data["Quote"]
                post_ask = float(post_quote.get("Ask", 0))
                post_bid = float(post_quote.get("Bid", 0))
                post_mid = (post_ask + post_bid) / 2

                orders_data.append(
                    {
                        "order_id": order_id,
                        "side": side,
                        "pre_mid": pre_mid,
                        "post_mid": post_mid,
                        "filled": True,
                        "latency_ms": latency_ms,
                    }
                )

                logger.info(
                    f"Order {i+1}/{num_trades} filled: ID {order_id}, latency: {latency_ms:.2f} ms"
                )
            else:
                logger.warning(f"Order {i+1}/{num_trades} filled but no post-trade quote")
        elif "OrderRejected" in order_result:
            reason = order_result.get("Reason", "Unknown reason")
            logger.warning(f"Order {i+1}/{num_trades} rejected: {reason}")

            orders_data.append(
                {
                    "side": side,
                    "pre_mid": pre_mid,
                    "filled": False,
                    "reason": reason,
                    "latency_ms": latency_ms,
                }
            )
        else:
            logger.warning(f"Order {i+1}/{num_trades} status unclear: {order_result}")

        time.sleep(interval)

    fill_rate = (orders_filled / orders_placed) * 100 if orders_placed > 0 else 0

    profitable_trades = 0
    unprofitable_trades = 0

    for order in orders_data:
        if order.get("filled", False):
            if order["side"] == "Buy" and order["post_mid"] > order["pre_mid"]:
                profitable_trades += 1
            elif order["side"] == "Sell" and order["post_mid"] < order["pre_mid"]:
                profitable_trades += 1
            else:
                unprofitable_trades += 1

    pf = profitable_trades / unprofitable_trades if unprofitable_trades > 0 else profitable_trades
    performance_factor = pf

    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    logger.info("Canary test results:")
    logger.info(f"- Trades placed: {orders_placed}")
    logger.info(f"- Trades filled: {orders_filled}")
    logger.info(f"- Fill rate: {fill_rate:.2f}%")
    logger.info(f"- Profitable trades: {profitable_trades}")
    logger.info(f"- Unprofitable trades: {unprofitable_trades}")
    logger.info(f"- Performance factor: {performance_factor:.2f}")
    logger.info(f"- Average latency: {avg_latency:.2f} ms")

    if fill_rate < 92:
        logger.error(f"Fill rate {fill_rate:.2f}% below target of 92%")
    else:
        logger.info(f"Fill rate {fill_rate:.2f}% meets or exceeds target of 92%")

    if performance_factor < 0.9:
        logger.error(f"Performance factor {performance_factor:.2f} below target of 0.9")
    else:
        logger.info(f"Performance factor {performance_factor:.2f} meets or exceeds target of 0.9")

    if avg_latency > 250:
        logger.error(f"Average latency {avg_latency:.2f} ms exceeds target of 250 ms")
    else:
        logger.info(f"Average latency {avg_latency:.2f} ms meets target of ≤ 250 ms")

    return fill_rate, performance_factor, orders_data


if __name__ == "__main__":
    instrument = DEFAULT_INSTRUMENT
    num_trades = DEFAULT_TRADES
    lot_size = DEFAULT_LOT_SIZE
    interval = DEFAULT_INTERVAL

    if len(sys.argv) > 1:
        instrument = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            num_trades = int(sys.argv[2])
        except ValueError:
            logger.error("Number of trades must be an integer")
            sys.exit(1)
    if len(sys.argv) > 3:
        try:
            lot_size = float(sys.argv[3])
        except ValueError:
            logger.error("Lot size must be a number")
            sys.exit(1)

    fill_rate, pf, orders_data = run_canary_test(instrument, num_trades, lot_size, interval)

    import json
    import datetime
    from pathlib import Path

    reports_dir = Path(__file__).parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = reports_dir / f"canary_{instrument}_{timestamp}.json"

    latencies = []
    for order in orders_data:
        if "latency_ms" in order:
            latencies.append(order["latency_ms"])

    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    # Count orders placed and filled from orders_data
    orders_placed = len(orders_data)
    orders_filled = sum(1 for order in orders_data if order.get("filled", False))

    with open(json_path, "w") as f:
        json.dump(
            {
                "instrument": instrument,
                "timestamp": timestamp,
                "metrics": {
                    "fill_rate": fill_rate,
                    "performance_factor": pf,
                    "avg_latency_ms": avg_latency,
                    "orders_placed": orders_placed,
                    "orders_filled": orders_filled,
                },
                "orders": orders_data,
            },
            f,
            indent=2,
        )

    logger.info(f"Stored raw fills JSON at {json_path}")

    if fill_rate >= 92 and pf >= 0.9:
        sys.exit(0)
    else:
        sys.exit(1)
