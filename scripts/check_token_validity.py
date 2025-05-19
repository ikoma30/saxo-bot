#!/usr/bin/env python3
"""
Check the validity of Saxo Bank API refresh tokens.

This script verifies that refresh tokens can successfully be exchanged for access tokens.
"""

import logging
import sys
from pathlib import Path

from src.core.saxo_client import SaxoClient

sys.path.append(str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("token_validity")


def check_token_validity(environment: str) -> bool:
    """
    Check if the refresh token for the specified environment is valid.

    Args:
        environment: Either "live" or "sim"

    Returns:
        bool: True if token is valid, False otherwise
    """
    client = SaxoClient(environment=environment)

    if not client.client_id:
        logger.error(f"{environment.upper()}_CLIENT_ID environment variable not set")
        return False
    if not client.client_secret:
        logger.error(f"{environment.upper()}_CLIENT_SECRET environment variable not set")
        return False
    if not client.refresh_token:
        logger.error(f"{environment.upper()}_REFRESH_TOKEN environment variable not set")
        return False

    try:
        result = client.authenticate()
        if result:
            logger.info(f"{environment.upper()}_REFRESH_TOKEN is valid")
            return True
        else:
            logger.error(f"{environment.upper()}_REFRESH_TOKEN is invalid or expired")
            return False
    except Exception as e:
        logger.error(f"Error checking {environment.upper()}_REFRESH_TOKEN: {str(e)}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        env = sys.argv[1].lower()
        if env not in ["live", "sim"]:
            logger.error("Environment must be either 'live' or 'sim'")
            sys.exit(1)
    else:
        env = "sim"  # Default to sim environment

    valid = check_token_validity(env)
    sys.exit(0 if valid else 1)
