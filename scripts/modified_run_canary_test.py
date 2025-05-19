#!/usr/bin/env python3
"""
Run a canary test with small lot sizes to verify trading functionality.

This script executes a specified number of trades with minimal lot size (0.01)
to validate the trading system in the simulation environment.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
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
REPORTS_DIR = Path(__file__).parent.parent / "reports"


def run_canary_test(
    instrument: str = DEFAULT_INSTRUMENT,
    num_trades: int = DEFAULT_TRADES,
    lot_size: float = DEFAULT_LOT_SIZE,
    interval: int = DEFAULT_INTERVAL,
    save_report: bool = True,
    bot_name: str = "Main",
) -> tuple[float, float, list[dict]]:
    """
    Run a canary test with small trades.

    Args:
        instrument: The trading instrument (default: USDJPY)
        num_trades: Number of trades to execute (default: 10)
        lot_size: Lot size for trades (default: 0.01)
        interval: Time between trades in seconds (default: 5)
        save_report: Whether to save a JSON report (default: True)
        bot_name: Name of the bot for the report (default: "Main")

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

    logger.info(f"Starting canary test: {num_trades} trades of {lot_size} lots for {instrument}")

    for i in range(num_trades):
        side = "Buy" if i % 2 == 0 else "Sell"

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

        start_time = time.time()
        order_result = client.place_order(
            instrument=instrument,
            order_type="Market",
            side=side,
            amount=Decimal(str(lot_size)),
        )
        latency_ms = (time.time() - start_time) * 1000

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
                        "timestamp": datetime.now().isoformat(),
                    }
                )

                logger.info(f"Order {i+1}/{num_trades} filled: ID {order_id}")
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
                    "timestamp": datetime.now().isoformat(),
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

    logger.info("Canary test results:")
    logger.info(f"- Trades placed: {orders_placed}")
    logger.info(f"- Trades filled: {orders_filled}")
    logger.info(f"- Fill rate: {fill_rate:.2f}%")
    logger.info(f"- Profitable trades: {profitable_trades}")
    logger.info(f"- Unprofitable trades: {unprofitable_trades}")
    logger.info(f"- Performance factor: {performance_factor:.2f}")

    if fill_rate < 92:
        logger.error(f"Fill rate {fill_rate:.2f}% below target of 92%")
    else:
        logger.info(f"Fill rate {fill_rate:.2f}% meets or exceeds target of 92%")

    if performance_factor < 0.9:
        logger.error(f"Performance factor {performance_factor:.2f} below target of 0.9")
    else:
        logger.info(f"Performance factor {performance_factor:.2f} meets or exceeds target of 0.9")

    if save_report:
        os.makedirs(REPORTS_DIR, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_data = {
            "bot_name": bot_name,
            "instrument": instrument,
            "timestamp": timestamp,
            "metrics": {
                "fill_rate": fill_rate,
                "performance_factor": performance_factor,
                "orders_placed": orders_placed,
                "orders_filled": orders_filled,
                "profitable_trades": profitable_trades,
                "unprofitable_trades": unprofitable_trades,
            },
            "orders": orders_data,
        }

        report_file = REPORTS_DIR / f"canary_{bot_name.lower()}_{timestamp}.json"
        with open(report_file, "w") as f:
            json.dump(report_data, f, indent=2)

        logger.info(f"Canary report saved to {report_file}")

    return fill_rate, performance_factor, orders_data


if __name__ == "__main__":
    instrument = DEFAULT_INSTRUMENT
    num_trades = DEFAULT_TRADES
    lot_size = DEFAULT_LOT_SIZE
    interval = DEFAULT_INTERVAL
    bot_name = "Main"

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
    if len(sys.argv) > 4:
        bot_name = sys.argv[4]

    fill_rate, pf, _ = run_canary_test(instrument, num_trades, lot_size, interval, True, bot_name)

    if fill_rate >= 92 and pf >= 0.9:
        sys.exit(0)
    else:
        sys.exit(1)
