#!/usr/bin/env python3
"""
Query Prometheus for specific metrics and save them to a file.

This script queries the Prometheus API for the specified metrics and
saves the results to a JSON file in the reports directory.
"""

import datetime
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("prometheus")

PROMETHEUS_PORT = 9090
REPORTS_DIR = Path(__file__).parent.parent / "reports"

METRICS = [
    "bot_order_attempt_total",
    "bot_order_filled_total",
    "slippage_guard_rejected_total",
]


def query_prometheus_metric(metric_name: str) -> dict[str, Any]:
    """
    Query Prometheus for a specific metric.

    Args:
        metric_name: Name of the metric to query

    Returns:
        dict: Metric data from Prometheus
    """
    try:
        url = f"http://localhost:{PROMETHEUS_PORT}/api/v1/query"
        params = {"query": metric_name}

        logger.info(f"Querying Prometheus for metric: {metric_name}")
        response = requests.get(url, params=params, timeout=5)

        if response.status_code != 200:
            logger.error(f"Failed to query metric {metric_name}: HTTP {response.status_code}")
            return {"status": "error", "error": f"HTTP {response.status_code}"}

        data: dict[str, Any] = response.json()
        logger.info(f"Successfully queried metric: {metric_name}")
        return data
    except requests.RequestException as e:
        logger.error(f"Failed to query Prometheus: {str(e)}")
        return {"status": "error", "error": str(e)}


def get_prometheus_metrics() -> str:
    """
    Query Prometheus for all specified metrics and save to a file.

    Returns:
        str: Path to the saved metrics file
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)

    metrics_data = {}
    for metric in METRICS:
        metrics_data[metric] = query_prometheus_metric(metric)

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


def main() -> int:
    """
    Query Prometheus for metrics and save to a file.

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    try:
        metrics_file = get_prometheus_metrics()
        logger.info(f"Successfully saved Prometheus metrics to {metrics_file}")
        return 0
    except Exception as e:
        logger.error(f"Failed to get Prometheus metrics: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
