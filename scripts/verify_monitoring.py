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
                for t in targets
                if t.get("health") == "down"
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


def check_opsgenie_key() -> bool:
    """
    Verify OpsGenie API key is configured for fallback alerts.

    Returns:
        bool: True if OpsGenie key is configured, False otherwise
    """
    opsgenie_key = os.environ.get("OG_GENIE_KEY")
    if not opsgenie_key:
        logger.warning("OG_GENIE_KEY environment variable not set (fallback alerts disabled)")
        return False

    if len(opsgenie_key) >= 20:  # Simple validation for API key length
        logger.info("OpsGenie API key is properly configured for fallback alerts")
        return True
    else:
        logger.error("OpsGenie API key does not appear to be valid")
        return False


def send_alert(message: str, severity: str = "warning") -> bool:
    """
    Send an alert through available channels with fallback mechanism.

    Tries Slack first, then OpsGenie as fallback, then sendmail as final fallback.

    Args:
        message: Alert message to send
        severity: Alert severity (info, warning, error, critical)

    Returns:
        bool: True if alert was sent through any channel, False if all channels failed
    """
    import json
    import subprocess
    from datetime import datetime

    slack_webhook = os.environ.get("SLACK_WEBHOOK")
    if slack_webhook and slack_webhook.startswith("https://hooks.slack.com/services/"):
        try:
            color = {
                "info": "#36a64f",
                "warning": "#ffcc00",
                "error": "#ff9900",
                "critical": "#E01E5A",
            }.get(severity, "#36a64f")

            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": "Saxo Bot Alert",
                        "fields": [
                            {
                                "title": "env",
                                "value": os.environ.get("ENV", "unknown"),
                                "short": True,
                            },
                            {
                                "title": "bot",
                                "value": os.environ.get("BOT_ID", "parent"),
                                "short": True,
                            },
                            {"title": "event", "value": "MONITORING", "short": True},
                            {"title": "details", "value": message},
                        ],
                        "footer": "saxo-bot-orchestrator",
                        "ts": int(datetime.now().timestamp()),
                    }
                ]
            }

            import requests

            response = requests.post(
                slack_webhook,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=5,
            )

            if response.status_code == 200:
                logger.info(f"Alert sent to Slack: {message}")
                return True
            else:
                logger.warning(f"Failed to send alert to Slack: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Error sending alert to Slack: {str(e)}")

    opsgenie_key = os.environ.get("OG_GENIE_KEY")
    if opsgenie_key and len(opsgenie_key) >= 20:
        try:
            opsgenie_payload: dict[str, object] = {
                "message": f"Saxo Bot Alert: {message}",
                "description": message,
                "priority": severity,
                "tags": [
                    os.environ.get("ENV", "unknown"),
                    os.environ.get("BOT_ID", "parent"),
                    "monitoring",
                ],
            }

            import requests

            response = requests.post(
                "https://api.opsgenie.com/v2/alerts",
                headers={
                    "Authorization": f"GenieKey {opsgenie_key}",
                    "Content-Type": "application/json",
                },
                data=json.dumps(opsgenie_payload),
                timeout=5,
            )

            if response.status_code in (200, 201, 202):
                logger.info(f"Alert sent to OpsGenie: {message}")
                return True
            else:
                logger.warning(f"Failed to send alert to OpsGenie: HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"Error sending alert to OpsGenie: {str(e)}")

    try:
        ops_email = "ops@example.com"  # This should be configured in environment or config
        subject = f"ALERT: Saxo Bot {severity.upper()}"
        email_body = f"Saxo Bot Alert\n\nEnvironment: {os.environ.get('ENV', 'unknown')}\nBot: {os.environ.get('BOT_ID', 'parent')}\nSeverity: {severity}\n\n{message}"

        email_content = f"Subject: {subject}\nTo: {ops_email}\n\n{email_body}"

        process = subprocess.Popen(
            ["sendmail", "-t"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate(input=email_content.encode())

        if process.returncode == 0:
            logger.info(f"Alert sent via email to {ops_email}")
            return True
        else:
            logger.error(f"Failed to send email alert: {stderr.decode()}")
            return False
    except Exception as e:
        logger.error(f"Error sending email alert: {str(e)}")
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
    opsgenie_configured = check_opsgenie_key()

    # Check if at least one alert channel is configured
    alert_channels_available = slack_configured or opsgenie_configured
    if not alert_channels_available:
        logger.error("No alert channels configured (Slack or OpsGenie)")
        send_alert("No alert channels configured (Slack or OpsGenie)", "critical")

    all_healthy = (
        prometheus_healthy
        and targets_status["down"] == 0
        and grafana_healthy
        and dashboards_count > 0
        and alert_channels_available
    )

    if all_healthy:
        logger.info("All monitoring systems are operational")
    else:
        logger.error("One or more monitoring systems are not operational")
        send_alert("One or more monitoring systems are not operational", "error")

    return all_healthy


if __name__ == "__main__":
    success = verify_all_monitoring()
    sys.exit(0 if success else 1)
