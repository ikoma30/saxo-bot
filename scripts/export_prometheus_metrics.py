#!/usr/bin/env python3
"""
Export Prometheus metrics to JSON.

This script connects to the Prometheus endpoint and exports metrics to a JSON file.
"""

import json
import logging
import os
import sys
import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("prometheus_export")


def export_metrics(
    metrics: list[str] = [
        "account_mu_pct",
        "daily_dd_pct",
        "net_exposure_jpy",
        "price_stream_gap_ms",
        "ws_drop_count",
        "oauth_refresh_fail_total",
        "bot_state",
        "order_throttle_gap_ms",
        "rate_limit_remaining_pct",
    ]
) -> str:
    """
    Export Prometheus metrics to a JSON file.
    
    Args:
        metrics: List of metric names to export
    
    Returns:
        str: Path to the generated JSON file
    """
    try:
        import requests
        
        prometheus_url = os.environ.get("PROMETHEUS_URL", "http://localhost:9090/prom_mock_endpoint")
        
        logger.info(f"Connecting to Prometheus at {prometheus_url}")
        
        metrics_data = {}
        
        for metric in metrics:
            query_url = f"{prometheus_url}?query={metric}"
            
            response = requests.get(query_url)
            response.raise_for_status()
            
            result = response.json()
            
            if result["status"] == "success" and "data" in result and "result" in result["data"]:
                metrics_data[metric] = result["data"]["result"]
            else:
                logger.warning(f"No data for metric {metric}")
                metrics_data[metric] = []
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = f"reports/prometheus_metrics_{timestamp}.json"
        
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, "w") as f:
            json.dump(metrics_data, f, indent=2)
        
        logger.info(f"Exported metrics to {json_path}")
        return json_path
        
    except Exception as e:
        logger.error(f"Error exporting Prometheus metrics: {str(e)}")
        return ""


if __name__ == "__main__":
    metrics = [
        "account_mu_pct",
        "daily_dd_pct",
        "net_exposure_jpy",
        "price_stream_gap_ms",
        "ws_drop_count",
        "oauth_refresh_fail_total",
        "bot_state",
        "order_throttle_gap_ms",
        "rate_limit_remaining_pct",
    ]
    
    if len(sys.argv) > 1:
        metrics = sys.argv[1].split(",")
    
    json_path = export_metrics(metrics)
    
    if json_path:
        print(f"Metrics exported to: {json_path}")
        sys.exit(0)
    else:
        print("Failed to export metrics")
        sys.exit(1)
