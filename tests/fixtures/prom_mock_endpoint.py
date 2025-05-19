#!/usr/bin/env python3
"""
Mock Prometheus endpoint for testing.

This script provides a mock Prometheus endpoint that returns
predefined metrics data for testing purposes.
"""

import json
from typing import Any, Dict

MOCK_METRICS = {
    "bot_order_attempt_total": {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {
                        "__name__": "bot_order_attempt_total",
                        "bot": "main",
                        "instance": "localhost:9090",
                        "job": "saxo-bot",
                    },
                    "value": [1716108405, "42"],
                },
                {
                    "metric": {
                        "__name__": "bot_order_attempt_total",
                        "bot": "micro-rev",
                        "instance": "localhost:9090",
                        "job": "saxo-bot",
                    },
                    "value": [1716108405, "38"],
                },
            ],
        },
    },
    "bot_order_filled_total": {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {
                        "__name__": "bot_order_filled_total",
                        "bot": "main",
                        "instance": "localhost:9090",
                        "job": "saxo-bot",
                    },
                    "value": [1716108405, "39"],
                },
                {
                    "metric": {
                        "__name__": "bot_order_filled_total",
                        "bot": "micro-rev",
                        "instance": "localhost:9090",
                        "job": "saxo-bot",
                    },
                    "value": [1716108405, "35"],
                },
            ],
        },
    },
    "slippage_guard_rejected_total": {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {
                        "__name__": "slippage_guard_rejected_total",
                        "bot": "main",
                        "instance": "localhost:9090",
                        "job": "saxo-bot",
                    },
                    "value": [1716108405, "3"],
                },
                {
                    "metric": {
                        "__name__": "slippage_guard_rejected_total",
                        "bot": "micro-rev",
                        "instance": "localhost:9090",
                        "job": "saxo-bot",
                    },
                    "value": [1716108405, "3"],
                },
            ],
        },
    },
}


def get_mock_metric(metric_name: str) -> Dict[str, Any]:
    """
    Get mock data for a specific metric.

    Args:
        metric_name: Name of the metric to get data for

    Returns:
        dict: Mock metric data
    """
    if metric_name in MOCK_METRICS:
        return MOCK_METRICS[metric_name]
    else:
        return {
            "status": "error",
            "errorType": "bad_data",
            "error": f"Unknown metric: {metric_name}",
        }


if __name__ == "__main__":
    print(json.dumps(MOCK_METRICS, indent=2))
