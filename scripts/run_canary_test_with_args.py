#!/usr/bin/env python3
"""
Run a canary test with small lot sizes to verify trading functionality.

This script executes a specified number of trades with minimal lot size (0.01)
to validate the trading system in the simulation environment.
"""

import argparse
import datetime
import json
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


def main() -> int:
    """
    Parse command line arguments and run canary test.

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(description="Run a canary test with small trades")
    parser.add_argument("--instrument", default=DEFAULT_INSTRUMENT, help="Trading instrument (default: USDJPY)")
    parser.add_argument("--trades", type=int, default=DEFAULT_TRADES, help="Number of trades to execute (default: 10)")
    parser.add_argument("--lot", type=float, default=DEFAULT_LOT_SIZE, help="Lot size for trades (default: 0.01)")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="Time between trades in seconds (default: 5)")
    
    args = parser.parse_args()
    
    fill_rate, pf, orders_data = run_canary_test(
        instrument=args.instrument,
        num_trades=args.trades,
        lot_size=args.lot,
        interval=args.interval,
    )

    reports_dir = Path(__file__).parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = reports_dir / f"canary_{args.instrument}_{timestamp}.json"
    html_path = reports_dir / "saxo_trader_go.html"

    latencies = []
    for order in orders_data:
        if "latency_ms" in order:
            latencies.append(order["latency_ms"])

    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    orders_placed = len(orders_data)
    orders_filled = sum(1 for order in orders_data if order.get("filled", False))

    with open(json_path, "w") as f:
        json.dump(
            {
                "instrument": args.instrument,
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

    with open(html_path, "w") as f:
        f.write(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Saxo Trade Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #0066cc; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                tr:hover {{ background-color: #f5f5f5; }}
                .summary {{ background-color: #e6f2ff; padding: 15px; border-radius: 5px; }}
                .metrics {{ margin-top: 20px; }}
                .pass {{ color: green; }}
                .fail {{ color: red; }}
            </style>
        </head>
        <body>
            <h1>Saxo Canary Test Report</h1>
            <p>Generated on {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            
            <div class="summary">
                <h2>Test Summary</h2>
                <p>Instrument: {args.instrument}</p>
                <p>Trades: {args.trades}</p>
                <p>Lot Size: {args.lot}</p>
            </div>
            
            <div class="metrics">
                <h2>KPI Metrics</h2>
                <table>
                    <tr><th>Metric</th><th>Value</th><th>Target</th><th>Status</th></tr>
                    <tr>
                        <td>Fill Rate</td>
                        <td>{fill_rate:.2f}%</td>
                        <td>≥ 92%</td>
                        <td class="{'pass' if fill_rate >= 92 else 'fail'}">{'PASS' if fill_rate >= 92 else 'FAIL'}</td>
                    </tr>
                    <tr>
                        <td>Performance Factor</td>
                        <td>{pf:.2f}</td>
                        <td>≥ 0.9</td>
                        <td class="{'pass' if pf >= 0.9 else 'fail'}">{'PASS' if pf >= 0.9 else 'FAIL'}</td>
                    </tr>
                    <tr>
                        <td>Average Latency</td>
                        <td>{avg_latency:.2f} ms</td>
                        <td>≤ 250 ms</td>
                        <td class="{'pass' if avg_latency <= 250 else 'fail'}">{'PASS' if avg_latency <= 250 else 'FAIL'}</td>
                    </tr>
                </table>
            </div>
            
            <h2>Trade Details</h2>
            <table>
                <tr>
                    <th>Order ID</th>
                    <th>Side</th>
                    <th>Pre-Mid</th>
                    <th>Post-Mid</th>
                    <th>Filled</th>
                    <th>Latency (ms)</th>
                </tr>
        """)
        
        for order in orders_data:
            f.write(f"""
                <tr>
                    <td>{order.get('order_id', 'N/A')}</td>
                    <td>{order.get('side', 'N/A')}</td>
                    <td>{order.get('pre_mid', 'N/A')}</td>
                    <td>{order.get('post_mid', 'N/A')}</td>
                    <td>{'Yes' if order.get('filled', False) else 'No'}</td>
                    <td>{order.get('latency_ms', 'N/A')}</td>
                </tr>
            """)
            
        f.write("""
            </table>
            
            <p>Account information has been redacted for security reasons.</p>
        </body>
        </html>
        """)

    logger.info(f"Stored raw fills JSON at {json_path}")
    logger.info(f"Generated HTML report at {html_path}")

    if fill_rate >= 92 and pf >= 0.9 and avg_latency <= 250:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
