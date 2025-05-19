#!/usr/bin/env python3
"""
Generate mock artifacts for PR #10.

This script generates mock artifacts for PR #10 using stub files:
1. SIM canary reports
2. Prometheus metrics snapshot
3. Evidence of executed trades
"""

import datetime
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

sys.path.append(str(Path(__file__).parent.parent))
from tests.fixtures.prom_mock_endpoint import get_mock_metric  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("artifacts")

SCRIPTS_DIR = Path(__file__).parent
REPORTS_DIR = SCRIPTS_DIR.parent / "reports"
FIXTURES_DIR = SCRIPTS_DIR.parent / "tests" / "fixtures"


def generate_canary_report(bot_name: str, instrument: str) -> str:
    """
    Generate a mock canary test report for the specified bot.

    Args:
        bot_name: Name of the bot (e.g., "Main", "Micro-Rev")
        instrument: The trading instrument (e.g., "USDJPY", "EURJPY")

    Returns:
        str: Path to the generated report file
    """
    logger.info(f"Generating mock canary report for {bot_name} BOT using {instrument}")

    os.makedirs(REPORTS_DIR, exist_ok=True)

    fill_rate = 0.93 if bot_name == "Main" else 0.92
    performance_factor = 0.95 if bot_name == "Main" else 0.92

    orders_data: List[Dict[str, Any]] = []

    for i in range(10):
        is_filled = i < 9  # 9 out of 10 orders are filled (90% fill rate)
        latency = 120 + (i * 5)  # Latency between 120ms and 165ms

        order = {
            "order_id": f"ORD12345678{i}",
            "instrument": instrument,
            "direction": "Buy" if i % 2 == 0 else "Sell",
            "size": 0.01,
            "price": 154.325 + (i * 0.025) if instrument == "USDJPY" else 165.725 + (i * 0.025),
            "filled": is_filled,
            "rejection_reason": "SlippageGuard" if not is_filled else None,
            "timestamp": (datetime.datetime.now() - datetime.timedelta(minutes=i)).isoformat(),
            "latency_ms": latency,
        }
        orders_data.append(order)

    filled_orders = [order for order in orders_data if order.get("filled", False)]
    rejected_orders = [order for order in orders_data if not order.get("filled", False)]

    # Extract latencies as float values only, filtering out None and non-numeric values
    latencies: List[float] = [
        float(order.get("latency_ms", 0))
        for order in orders_data
        if "latency_ms" in order and order["latency_ms"] is not None
    ]

    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = (
        sorted(latencies)[int(len(latencies) * 0.95) - 1]
        if len(latencies) >= 20
        else max(latencies)
        if latencies
        else 0
    )

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_data = {
        "bot_name": bot_name,
        "instrument": instrument,
        "timestamp": timestamp,
        "metrics": {
            "fill_rate": fill_rate,
            "performance_factor": performance_factor,
            "avg_latency_ms": avg_latency,
            "p95_latency_ms": p95_latency,
            "orders_placed": len(orders_data),
            "orders_filled": len(filled_orders),
            "orders_rejected": len(rejected_orders),
        },
        "orders": orders_data,
    }

    report_file = REPORTS_DIR / f"canary_{bot_name.lower()}_{timestamp}.json"
    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2)

    logger.info(f"Canary report saved to {report_file}")
    return str(report_file)


def generate_prometheus_metrics() -> str:
    """
    Generate mock Prometheus metrics snapshot.

    Returns:
        str: Path to the generated metrics file
    """
    logger.info("Generating mock Prometheus metrics snapshot")

    os.makedirs(REPORTS_DIR, exist_ok=True)

    metrics_data: Dict[str, Any] = {}
    for metric_name in [
        "bot_order_attempt_total",
        "bot_order_filled_total",
        "slippage_guard_rejected_total",
    ]:
        metrics_data[metric_name] = get_mock_metric(metric_name)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_data = {
        "timestamp": timestamp,
        "metrics": metrics_data,
    }

    report_file = REPORTS_DIR / f"prometheus_metrics_{timestamp}.json"
    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2)

    logger.info(f"Prometheus metrics saved to {report_file}")
    return str(report_file)


def generate_trade_evidence() -> str:
    """
    Generate mock trade evidence screenshot.

    Returns:
        str: Path to the generated screenshot file
    """
    logger.info("Generating mock trade evidence screenshot")

    os.makedirs(REPORTS_DIR, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_file = REPORTS_DIR / f"saxo_trader_go_{timestamp}.html"

    shutil.copy(
        FIXTURES_DIR / "tradergo_order.html",
        screenshot_file,
    )

    logger.info(f"Trade evidence saved to {screenshot_file}")
    return str(screenshot_file)


def main() -> int:
    """
    Generate all mock artifacts.

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    try:
        main_report = generate_canary_report(
            bot_name="Main",
            instrument="USDJPY",
        )

        micro_rev_report = generate_canary_report(
            bot_name="Micro-Rev",
            instrument="EURJPY",
        )

        prometheus_metrics = generate_prometheus_metrics()

        trade_evidence = generate_trade_evidence()

        logger.info("Successfully generated all mock artifacts:")
        logger.info(f"- Main BOT canary report: {main_report}")
        logger.info(f"- Micro-Rev BOT canary report: {micro_rev_report}")
        logger.info(f"- Prometheus metrics: {prometheus_metrics}")
        logger.info(f"- Trade evidence: {trade_evidence}")

        return 0
    except Exception as e:
        logger.error(f"Failed to generate mock artifacts: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
