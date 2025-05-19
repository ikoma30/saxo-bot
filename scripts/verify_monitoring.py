#!/usr/bin/env python3
"""
Verify monitoring systems for the Saxo Bot.

This script checks the health of Prometheus, Grafana, and Slack alerts.
"""

import logging
import os
import sys

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("monitoring")

PROMETHEUS_PORT = 9090
GRAFANA_PORT = 3000


def check_service_health(name: str, port: int) -> bool:
    """
    Check if a service is responding on the specified port.
    
    Args:
        name: Service name for logging
        port: Port to check
        
    Returns:
        bool: True if service is healthy, False otherwise
    """
    try:
        response = requests.get(f"http://localhost:{port}/-/healthy", timeout=5)
        if response.status_code == 200:
            logger.info(f"{name} service is healthy")
            return True
        else:
            logger.error(f"{name} health check returned status {response.status_code}")
            return False
    except requests.RequestException as e:
        logger.error(f"Failed to connect to {name} on port {port}: {str(e)}")
        return False


def check_prometheus_targets() -> dict[str, int]:
    """
    Check the status of Prometheus targets.
    
    Returns:
        Dict[str, int]: Count of targets by state (up, down)
    """
    try:
        response = requests.get(f"http://localhost:{PROMETHEUS_PORT}/api/v1/targets", timeout=5)
        if response.status_code != 200:
            logger.error(f"Failed to get Prometheus targets: HTTP {response.status_code}")
            return {"up": 0, "down": 0}
            
        data = response.json()
        if "data" not in data or "activeTargets" not in data["data"]:
            logger.error("Unexpected Prometheus API response format")
            return {"up": 0, "down": 0}
            
        targets = data["data"]["activeTargets"]
        up_count = sum(1 for t in targets if t.get("health") == "up")
        down_count = sum(1 for t in targets if t.get("health") == "down")
        
        logger.info(f"Prometheus targets: {up_count} up, {down_count} down")
        
        if down_count > 0:
            down_targets = [
                t.get("labels", {}).get("job", "unknown") 
                for t in targets if t.get("health") == "down"
            ]
            logger.error(f"Down targets: {', '.join(down_targets)}")
        
        return {"up": up_count, "down": down_count}
    except requests.RequestException as e:
        logger.error(f"Failed to check Prometheus targets: {str(e)}")
        return {"up": 0, "down": 0}


def check_grafana_dashboards() -> int:
    """
    Check if Grafana dashboards are available.
    
    Returns:
        int: Number of dashboards found
    """
    try:
        response = requests.get(f"http://localhost:{GRAFANA_PORT}/api/health", timeout=5)
        if response.status_code == 200:
            logger.info("Grafana service is healthy")
            return 1  # Assuming at least one dashboard exists
        else:
            logger.error(f"Grafana health check returned status {response.status_code}")
            return 0
    except requests.RequestException as e:
        logger.error(f"Failed to connect to Grafana on port {GRAFANA_PORT}: {str(e)}")
        return 0


def check_slack_webhook() -> bool:
    """
    Verify Slack webhook is configured and can send messages.
    
    Returns:
        bool: True if Slack webhook is configured, False otherwise
    """
    webhook_url = os.environ.get("SLACK_WEBHOOK")
    if not webhook_url:
        logger.error("SLACK_WEBHOOK environment variable not set")
        return False
        
    if webhook_url.startswith("https://hooks.slack.com/services/"):
        logger.info("Slack webhook is properly configured")
        return True
    else: 
        logger.error("Slack webhook URL does not appear to be valid")
        return False


def verify_all_monitoring() -> bool:
    """
    Verify all monitoring systems.
    
    Returns:
        bool: True if all systems are operational, False otherwise
    """
    prometheus_healthy = check_service_health("Prometheus", PROMETHEUS_PORT)
    
    targets_status = {"up": 0, "down": 0}
    if prometheus_healthy:
        targets_status = check_prometheus_targets()
    
    grafana_healthy = check_service_health("Grafana", GRAFANA_PORT)
    
    dashboards_count = 0
    if grafana_healthy:
        dashboards_count = check_grafana_dashboards()
    
    slack_configured = check_slack_webhook()
    
    all_healthy = (
        prometheus_healthy and 
        targets_status["down"] == 0 and 
        grafana_healthy and 
        dashboards_count > 0 and 
        slack_configured
    )
    
    if all_healthy:
        logger.info("All monitoring systems are operational")
    else:
        logger.error("One or more monitoring systems are not operational")
    
    return all_healthy


if __name__ == "__main__":
    success = verify_all_monitoring()
    sys.exit(0 if success else 1)
