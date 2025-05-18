"""
Saxo Bank API Client Module

This module provides the SaxoClient class for interacting with the Saxo Bank OpenAPI.
"""

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)


class SaxoClient:
    """Client for interacting with the Saxo Bank OpenAPI."""

    def __init__(self, environment: str = "live") -> None:
        """
        Initialize the Saxo Bank API client.

        Args:
            environment: Either "live" or "sim" for production or simulation environment
        """
        self.environment = environment
        self.base_url = (
            "https://gateway.saxobank.com/sim/openapi"
            if environment == "sim"
            else "https://gateway.saxobank.com/openapi"
        )
        self.client_id = os.environ.get(f"{environment.upper()}_CLIENT_ID")
        self.client_secret = os.environ.get(f"{environment.upper()}_CLIENT_SECRET")
        self.refresh_token = os.environ.get(f"{environment.upper()}_REFRESH_TOKEN")
        self.account_key = os.environ.get(f"{environment.upper()}_ACCOUNT_KEY")
        self.access_token: str | None = None
        self.token_expiry: str | None = None

    def authenticate(self) -> bool:
        """
        Authenticate with the Saxo Bank API using the refresh token.

        Returns:
            bool: True if authentication was successful, False otherwise
        """
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            logger.error("Missing required authentication credentials")
            return False

        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        try:
            response = requests.post(f"{self.base_url}/token", data=data, timeout=30)
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            return bool(self.access_token)
        except requests.RequestException as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False

    def get_account_info(self) -> dict[str, Any] | None:
        """
        Get account information from the Saxo Bank API.

        Returns:
            dict[str, Any] | None: Account information or None if the request failed
        """
        if not self.access_token or not self.account_key:
            logger.error("Not authenticated or missing account key")
            return None

        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            response = requests.get(
                f"{self.base_url}/port/v1/accounts/{self.account_key}",
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            account_info: dict[str, Any] = response.json()
            return account_info
        except requests.RequestException as e:
            logger.error(f"Failed to get account info: {str(e)}")
            return None

    def get_positions(self) -> list[dict[str, Any]] | None:
        """
        Get current positions from the Saxo Bank API.

        Returns:
            list[dict[str, Any]] | None: List of positions or None if the request failed
        """
        if not self.access_token or not self.account_key:
            logger.error("Not authenticated or missing account key")
            return None

        headers = {"Authorization": f"Bearer {self.access_token}"}

        try:
            response = requests.get(
                f"{self.base_url}/port/v1/positions?FieldGroups=DisplayAndFormat",
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            response_data: dict[str, Any] = response.json()
            positions: list[dict[str, Any]] = response_data.get("Data", [])
            return positions
        except requests.RequestException as e:
            logger.error(f"Failed to get positions: {str(e)}")
            return None
