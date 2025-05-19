#!/usr/bin/env python3
"""
Generate canary test reports and save them as JSON files.

This script runs canary tests for both Main BOT and Micro-Rev BOT,
and saves the results as JSON files in the reports directory.
"""

import datetime
import json
import logging
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from scripts.modified_run_canary_test import run_canary_test  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("report")

REPORTS_DIR = Path(__file__).parent.parent / "reports"


def generate_canary_report(
    bot_name: str,
    instrument: str,
    num_trades: int = 10,
    lot_size: float = 0.01
) -> str:
    """
    Generate a canary test report for the specified bot.

    Args:
        bot_name: Name of the bot (e.g., "main", "micro-rev")
        instrument: The trading instrument (e.g., "USDJPY", "EURJPY")
        num_trades: Number of trades to execute (default: 10)
        lot_size: Lot size for trades (default: 0.01)

    Returns:
        str: Path to the generated report file
    """
    logger.info(f"Generating canary report for {bot_name} BOT using {instrument}")
    
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    fill_rate, performance_factor = run_canary_test(
        instrument=instrument,
        num_trades=num_trades,
        lot_size=lot_size,
    )
    
    orders_data = []
    
    filled_orders = [order for order in orders_data if order.get("filled", False)]
    rejected_orders = [order for order in orders_data if not order.get("filled", False)]
    
    latencies = [
        order.get("latency_ms", 0) 
        for order in orders_data 
        if "latency_ms" in order
    ]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = (
        sorted(latencies)[int(len(latencies) * 0.95) - 1] 
        if len(latencies) >= 20 
        else max(latencies) if latencies else 0
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


def main() -> int:
    """
    Generate canary reports for both Main BOT and Micro-Rev BOT.
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    try:
        main_report = generate_canary_report(
            bot_name="Main",
            instrument="USDJPY",
            num_trades=10,
            lot_size=0.01,
        )
        
        micro_rev_report = generate_canary_report(
            bot_name="Micro-Rev",
            instrument="EURJPY",
            num_trades=10,
            lot_size=0.01,
        )
        
        logger.info("Successfully generated canary reports:")
        logger.info(f"- Main BOT: {main_report}")
        logger.info(f"- Micro-Rev BOT: {micro_rev_report}")
        
        return 0
    except Exception as e:
        logger.error(f"Failed to generate canary reports: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
