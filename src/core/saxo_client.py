"""
Saxo Bank API Client Module

This module provides the SaxoClient class for interacting with the Saxo Bank OpenAPI,
with specific focus on trading operations.
"""

import logging
import os
from decimal import Decimal
from typing import Any

import requests

from src.common.exceptions import SaxoApiError
from src.common.retry_utils import retryable
from src.core.slippage_guard import SlippageGuard

logger = logging.getLogger("saxo")


class SaxoClient:
    """Client for interacting with the Saxo Bank OpenAPI with trading capabilities."""

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
        self.use_trade_v3 = os.environ.get("USE_TRADE_V3", "false").lower() == "true"
        self.timeout = 5  # 5 second timeout as per requirements
        self.slippage_guard = SlippageGuard()  # Initialize SlippageGuard

    @retryable(max_attempts=3, statuses=[429, 502, 503, 504])
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
            logger.info("Authenticating with Saxo Bank API")
            response = requests.post(f"{self.base_url}/token", data=data, timeout=self.timeout)
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            logger.info("Authentication successful")
            return bool(self.access_token)
        except requests.HTTPError as e:
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Authentication failed with status {e.response.status_code}")
                raise SaxoApiError(
                    "Authentication failed", e.response.status_code, e.response.json()
                ) from e
            else:
                logger.error(f"Authentication failed: {str(e)}")
                raise SaxoApiError("Authentication failed", None, None) from e
        except requests.RequestException as e:
            logger.error(f"Authentication request failed: {str(e)}")
            return False

    def _get_headers(self) -> dict[str, str]:
        """
        Get the headers for API requests.

        Returns:
            dict[str, str]: Headers with authorization token
        """
        if not self.access_token:
            raise ValueError("Not authenticated. Call authenticate() first.")

        return {"Authorization": f"Bearer {self.access_token}"}

    @retryable(max_attempts=3, statuses=[429, 502, 503, 504])
    def get_quote(self, instrument: str) -> dict[str, Any] | None:
        """
        Get a quote for the specified instrument.

        Args:
            instrument: The instrument identifier (e.g., "EURUSD")

        Returns:
            Optional[dict[str, Any]]: Quote information or None if the request failed
        """
        if not self.access_token:
            logger.error("Not authenticated")
            return None

        headers = self._get_headers()
        endpoint = "/trade/v1/prices/quotes"
        params = {"AssetType": "FxSpot", "Uic": instrument}

        try:
            logger.info(f"Getting quote for instrument {instrument}")
            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=headers,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            quote_data: dict[str, Any] = response.json()
            logger.info(f"Successfully retrieved quote for {instrument}")
            return quote_data
        except requests.HTTPError as e:
            if hasattr(e, "response") and e.response is not None:
                logger.error(
                    f"Failed to get quote for {instrument} with status {e.response.status_code}"
                )
                raise SaxoApiError(
                    f"Failed to get quote for {instrument}",
                    e.response.status_code,
                    e.response.json(),
                ) from e
            else:
                logger.error(f"Failed to get quote for {instrument}: {str(e)}")
                raise SaxoApiError(f"Failed to get quote for {instrument}", None, None) from e
        except requests.RequestException as e:
            logger.error(f"Quote request failed for {instrument}: {str(e)}")
            return None

    @retryable(max_attempts=3, statuses=[429, 502, 503, 504])
    def place_order(
        self,
        instrument: str,
        order_type: str,
        side: str,
        amount: int | float | Decimal,
        price: float | Decimal | None = None,
    ) -> dict[str, Any] | None:
        """
        Place an order for the specified instrument.

        Args:
            instrument: The instrument identifier (e.g., "EURUSD")
            order_type: The type of order (e.g., "Market", "Limit")
            side: The side of the order ("Buy" or "Sell")
            amount: The amount to trade
            price: The price for limit orders (optional)

        Returns:
            Optional[dict[str, Any]]: Order information or None if the request failed
        """
        if not self.access_token or not self.account_key:
            logger.error("Not authenticated or missing account key")
            return None

        headers = self._get_headers()

        trade_version = "v3" if self.use_trade_v3 else "v2"
        endpoint = f"/trade/{trade_version}/orders"

        precheck_result = self._precheck_order(instrument, order_type, side, amount, price)

        if not precheck_result:
            logger.error("Order precheck failed")
            return None

        if precheck_result.get("SlippageGuardRejection"):
            logger.error("Order rejected by SlippageGuard due to excessive spread")
            return {"OrderRejected": True, "Reason": "SlippageGuard: Excessive spread"}

        if precheck_result.get("BlockingDisclaimers"):
            for disclaimer in precheck_result.get("BlockingDisclaimers", []):
                disclaimer_id = disclaimer.get("Id")
                if not disclaimer_id:
                    continue

                if not self._accept_disclaimer(disclaimer_id):
                    logger.error(f"Failed to accept disclaimer {disclaimer_id}")
                    return None

            precheck_result = self._precheck_order(instrument, order_type, side, amount, price)

            if not precheck_result:
                logger.error("Order precheck failed after accepting disclaimers")
                return None

        order_data = {
            "AccountKey": self.account_key,
            "AssetType": "FxSpot",
            "Amount": str(amount),
            "BuySell": side,
            "OrderType": order_type,
            "Uic": instrument,
        }

        if price and order_type.lower() != "market":
            order_data["Price"] = str(price)

        try:
            logger.info(f"Placing {side} {order_type} order for {amount} {instrument}")
            response = requests.post(
                f"{self.base_url}{endpoint}",
                headers=headers,
                json=order_data,
                timeout=self.timeout,
            )
            response.raise_for_status()
            order_response: dict[str, Any] = response.json()
            logger.info(f"Successfully placed order: {order_response.get('OrderId')}")
            return order_response
        except requests.HTTPError as e:
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Failed to place order with status {e.response.status_code}")
                raise SaxoApiError(
                    "Failed to place order", e.response.status_code, e.response.json()
                ) from e
            else:
                logger.error(f"Failed to place order: {str(e)}")
                raise SaxoApiError("Failed to place order", None, None) from e
        except requests.RequestException as e:
            logger.error(f"Order request failed: {str(e)}")
            return None

    @retryable(max_attempts=3, statuses=[429, 502, 503, 504])
    def _precheck_order(
        self,
        instrument: str,
        order_type: str,
        side: str,
        amount: int | float | Decimal,
        price: float | Decimal | None = None,
    ) -> dict[str, Any] | None:
        """
        Precheck an order before placing it.

        Args:
            instrument: The instrument identifier (e.g., "EURUSD")
            order_type: The type of order (e.g., "Market", "Limit")
            side: The side of the order ("Buy" or "Sell")
            amount: The amount to trade
            price: The price for limit orders (optional)

        Returns:
            Optional[dict[str, Any]]: Precheck result or None if the request failed
        """
        if not self.access_token or not self.account_key:
            logger.error("Not authenticated or missing account key")
            return None

        quote_data = self.get_quote(instrument)
        if not quote_data or "Quote" not in quote_data:
            logger.error(f"Failed to get quote for {instrument}, cannot check spread")
            return None
        
        quote = quote_data["Quote"]
        ask = float(quote.get("Ask", 0))
        bid = float(quote.get("Bid", 0))
        mid = (ask + bid) / 2
        
        fill_price = ask if side == "Buy" else bid
        
        if not self.slippage_guard.check_slippage(instrument, mid, fill_price):
            logger.error(f"SlippageGuard rejected {side} order for {instrument} - excessive spread")
            return {"SlippageGuardRejection": True, "PreCheckResult": "Rejected"}

        headers = self._get_headers()

        trade_version = "v3" if self.use_trade_v3 else "v2"
        endpoint = f"/trade/{trade_version}/orders/precheck"

        order_data = {
            "AccountKey": self.account_key,
            "AssetType": "FxSpot",
            "Amount": str(amount),
            "BuySell": side,
            "OrderType": order_type,
            "Uic": instrument,
        }

        if price and order_type.lower() != "market":
            order_data["Price"] = str(price)

        try:
            logger.info(f"Prechecking {side} {order_type} order for {amount} {instrument}")
            response = requests.post(
                f"{self.base_url}{endpoint}",
                headers=headers,
                json=order_data,
                timeout=self.timeout,
            )
            response.raise_for_status()
            precheck_result: dict[str, Any] = response.json()
            logger.info("Order precheck completed")
            return precheck_result
        except requests.HTTPError as e:
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Order precheck failed with status {e.response.status_code}")
                raise SaxoApiError(
                    "Order precheck failed", e.response.status_code, e.response.json()
                ) from e
            else:
                logger.error(f"Order precheck failed: {str(e)}")
                raise SaxoApiError("Order precheck failed", None, None) from e
        except requests.RequestException as e:
            logger.error(f"Order precheck request failed: {str(e)}")
            return None

    @retryable(max_attempts=3, statuses=[429, 502, 503, 504])
    def _accept_disclaimer(self, disclaimer_id: str) -> bool:
        """
        Accept a disclaimer.

        Args:
            disclaimer_id: The ID of the disclaimer to accept

        Returns:
            bool: True if the disclaimer was accepted, False otherwise
        """
        if not self.access_token:
            logger.error("Not authenticated")
            return False

        headers = self._get_headers()
        endpoint = f"/trade/v1/disclaimers/{disclaimer_id}/accept"

        try:
            logger.info(f"Accepting disclaimer {disclaimer_id}")
            response = requests.put(
                f"{self.base_url}{endpoint}",
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.info(f"Successfully accepted disclaimer {disclaimer_id}")
            return True
        except requests.HTTPError as e:
            if hasattr(e, "response") and e.response is not None:
                logger.error(
                    f"Failed to accept disclaimer {disclaimer_id} "
                    f"with status {e.response.status_code}"
                )
                raise SaxoApiError(
                    f"Failed to accept disclaimer {disclaimer_id}",
                    e.response.status_code,
                    e.response.json(),
                ) from e
            else:
                logger.error(f"Failed to accept disclaimer {disclaimer_id}: {str(e)}")
                raise SaxoApiError(
                    f"Failed to accept disclaimer {disclaimer_id}", None, None
                ) from e
        except requests.RequestException as e:
            logger.error(f"Disclaimer acceptance request failed: {str(e)}")
            return False

    @retryable(max_attempts=3, statuses=[429, 502, 503, 504])
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.

        Args:
            order_id: The ID of the order to cancel

        Returns:
            bool: True if the order was cancelled, False otherwise
        """
        if not self.access_token:
            logger.error("Not authenticated")
            return False

        headers = self._get_headers()

        trade_version = "v3" if self.use_trade_v3 else "v2"
        endpoint = f"/trade/{trade_version}/orders/{order_id}"

        try:
            logger.info(f"Cancelling order {order_id}")
            response = requests.delete(
                f"{self.base_url}{endpoint}",
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.info(f"Successfully cancelled order {order_id}")
            return True
        except requests.HTTPError as e:
            if hasattr(e, "response") and e.response is not None:
                logger.error(
                    f"Failed to cancel order {order_id} with status {e.response.status_code}"
                )
                raise SaxoApiError(
                    f"Failed to cancel order {order_id}", e.response.status_code, e.response.json()
                ) from e
            else:
                logger.error(f"Failed to cancel order {order_id}: {str(e)}")
                raise SaxoApiError(f"Failed to cancel order {order_id}", None, None) from e
        except requests.RequestException as e:
            logger.error(f"Order cancellation request failed: {str(e)}")
            return False
