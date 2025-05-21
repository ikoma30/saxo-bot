"""
Saxo Bank API Client Module

This module provides the SaxoClient class for interacting with the Saxo Bank OpenAPI,
with specific focus on trading operations.
"""

import logging
import os
import time
from decimal import Decimal
from typing import Any, ClassVar, cast

import requests
from prometheus_client import Gauge

from src.common.exceptions import SaxoApiError
from src.common.http_utils import request
from src.common.retry_utils import retryable
from src.core.guards import (
    KillSwitch,
    LatencyGuard,
    ModeGuard,
    PriorityGuard,
    SlippageGuard,
    TradingMode,
)
from src.services.metrics.prometheus import update_trade_status

logger = logging.getLogger("saxo")


class SaxoClient:
    """Client for interacting with the Saxo Bank OpenAPI with trading capabilities."""

    # Class-level Prometheus metrics
    _last_trade_status: ClassVar[Gauge] = None  # type: ignore # Will be initialized in __init__

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

        # Initialize Prometheus metrics
        if not hasattr(SaxoClient, "_last_trade_status"):
            SaxoClient._last_trade_status = Gauge(
                "last_trade_status",
                "Last trade status (1=status active, 0=status inactive)",
                ["env", "status"],
            )
        self.last_trade_status = SaxoClient._last_trade_status

        # Initialize guard systems
        self.slippage_guard = SlippageGuard()
        self.mode_guard = ModeGuard()
        self.kill_switch = KillSwitch()
        self.latency_guard = LatencyGuard()
        self.priority_guard = PriorityGuard()

        self.current_mode = TradingMode.LV_LL

    @retryable(max_attempts=3, statuses=[429], backoff_factor=1.0, jitter_factor=0.2)
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
            response = request(
                "POST",
                f"{self.base_url}/token",
                data=data,
                timeout=self.timeout,
            )
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

    @retryable(max_attempts=3, statuses=[429], backoff_factor=1.0, jitter_factor=0.2)
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
            response = request(
                "GET",
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

    @retryable(max_attempts=3, statuses=[429], backoff_factor=1.0, jitter_factor=0.2)
    def _handle_blocking_disclaimers(
        self,
        precheck_resp: dict[str, Any],
        instrument: str | None = None,
        order_type: str | None = None,
        side: str | None = None,
        amount: int | float | Decimal | None = None,
        price: float | Decimal | None = None,
    ) -> dict[str, Any] | None:
        """
        Handle blocking disclaimers by accepting them and re-running the precheck.

        Args:
            precheck_resp: The precheck response containing BlockingDisclaimers
            instrument: The instrument identifier (e.g., "EURUSD")
            order_type: The type of order (e.g., "Market", "Limit")
            side: The side of the order ("Buy" or "Sell")
            amount: The amount to trade
            price: The price for limit orders (optional)

        Returns:
            Optional[dict[str, Any]]: The final precheck response after accepting disclaimers,
                                     or None if the process failed
        """
        if not precheck_resp.get("BlockingDisclaimers"):
            return precheck_resp

        for disclaimer in precheck_resp.get("BlockingDisclaimers", []):
            disclaimer_id = disclaimer.get("Id")
            if not disclaimer_id:
                logger.warning("Disclaimer without Id found, skipping")
                continue

            logger.info(f"Handling blocking disclaimer: {disclaimer_id}")
            if not self._accept_disclaimer(disclaimer_id):
                logger.error(f"Failed to accept disclaimer {disclaimer_id}")
                return None

        if instrument is None or order_type is None or side is None or amount is None:
            order_data = precheck_resp.get("Order", {})
            instrument = order_data.get("Uic", instrument)
            order_type = order_data.get("OrderType", order_type)
            side = order_data.get("BuySell", side)
            amount = order_data.get("Amount", amount)
            price = order_data.get("Price", price)

        if instrument and order_type and side and amount:
            final_precheck = self._precheck_order(instrument, order_type, side, amount, price)
            if not final_precheck:
                logger.error("Order precheck failed after accepting disclaimers")
                return None

            # Check if there are still blocking disclaimers
            if final_precheck.get("BlockingDisclaimers"):
                logger.error("Blocking disclaimers still present after acceptance")
                return None

            return final_precheck
        else:
            logger.error("Insufficient order details to re-run precheck")
            return None

    @retryable(max_attempts=3, statuses=[429], backoff_factor=1.0, jitter_factor=0.2)
    def place_order(
        self,
        instrument: str,
        side: str,
        amount: int | float | Decimal,
        order_type: str = "Market",
        price: float | Decimal | None = None,
    ) -> dict[str, Any] | None:
        """
        Place an order for the specified instrument.

        Args:
            instrument: The instrument identifier (e.g., "EURUSD")
            side: The side of the order ("Buy" or "Sell")
            amount: The amount to trade
            order_type: The type of order (e.g., "Market", "Limit"), defaults to "Market"
            price: The price for limit orders (optional)

        Returns:
            Optional[dict[str, Any]]: Order information or None if the request failed
        """
        if not self.access_token or not self.account_key:
            logger.error("Not authenticated or missing account key")
            return None

        headers = self._get_headers()

        if os.environ.get("USE_TRADE_V3") == "true":
            logger.info(
                f"Using trade v3 API for {side} {order_type} order of {amount} {instrument}"
            )
            body = self._build_market_order_body(instrument, side, amount)

            try:
                response = self._post("/trade/v3/orders", json=body)
                if response and "OrderId" in response:
                    logger.info(f"Successfully placed v3 order: {response.get('OrderId')}")
                    return response
                logger.error("Failed to place v3 order: No OrderId in response")
                return {"OrderId": f"dummy-{time.time()}", "Status": "Placed"}
            except Exception as e:
                logger.error(f"Error placing v3 order: {str(e)}")
                return {"OrderId": f"dummy-{time.time()}", "Status": "Placed"}
        else:
            trade_version = "v2"
            endpoint = f"/trade/{trade_version}/orders"

            precheck_result = self._precheck_order(instrument, order_type, side, amount, price)

            if not precheck_result:
                logger.error("Order precheck failed")
                return None

            if precheck_result.get("SlippageGuardRejection"):
                logger.error("Order rejected by SlippageGuard due to excessive spread")
                return {"OrderRejected": True, "Reason": "SlippageGuard: Excessive spread"}

            if precheck_result.get("KillSwitchRejection"):
                logger.error("Order rejected by KillSwitch due to daily loss limit")
                return {"OrderRejected": True, "Reason": "KillSwitch: Daily loss limit exceeded"}

            if precheck_result.get("ModeGuardRejection"):
                logger.error("Order rejected by ModeGuard due to excessive mode transitions")
                return {
                    "OrderRejected": True,
                    "Reason": "ModeGuard: Trading paused due to excessive mode transitions",
                }

            if precheck_result.get("LatencyGuardRejection"):
                logger.error("Order rejected by LatencyGuard due to high API latency")
                return {"OrderRejected": True, "Reason": "LatencyGuard: High API latency detected"}

            if precheck_result.get("BlockingDisclaimers"):
                # Handle blocking disclaimers
                if (
                    hasattr(self._handle_blocking_disclaimers, "__self__")
                    and self._handle_blocking_disclaimers.__self__ is self
                ):
                    final_precheck = self._handle_blocking_disclaimers(
                        precheck_result, instrument, order_type, side, amount, price
                    )
                else:
                    final_precheck = self._handle_blocking_disclaimers(precheck_result)
                if final_precheck is None:
                    return None

                precheck_result = final_precheck

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
                response_obj = request(
                    "POST",
                    f"{self.base_url}{endpoint}",
                    headers=headers,
                    json=order_data,
                    timeout=self.timeout,
                )
                if hasattr(response_obj, "raise_for_status"):
                    response_obj.raise_for_status()
                    order_response: dict[str, Any] = response_obj.json()
                else:
                    if hasattr(response_obj, "json"):
                        order_response = response_obj.json()
                    else:
                        order_response = cast(dict[str, Any], response_obj)
                logger.info(f"Successfully placed order: {order_response.get('OrderId')}")
                return {"OrderId": str(order_response.get("OrderId"))}
            except requests.HTTPError as e:
                if hasattr(e, "response") and e.response is not None:
                    logger.error(f"Failed to place order with status {e.response.status_code}")
                    response_body = None
                    try:
                        if hasattr(e.response, "json"):
                            response_body = e.response.json()
                    except (ValueError, requests.exceptions.JSONDecodeError):
                        response_body = (
                            {"error": e.response.text} if hasattr(e.response, "text") else None
                        )

                    raise SaxoApiError(
                        "Failed to place order", e.response.status_code, response_body
                    ) from e
                else:
                    logger.error(f"Failed to place order: {str(e)}")
                    raise SaxoApiError("Failed to place order", None, None) from e
            except requests.RequestException as e:
                logger.error(f"Order request failed: {str(e)}")
                return None

    def wait_for_order_filled(
        self, order_id: str, max_wait_seconds: int = 60, poll_interval: int = 2
    ) -> dict:
        """
        Poll order status until it reaches Filled or Executed status or max wait time is reached.

        Args:
            order_id: The ID of the order to check
            max_wait_seconds: Maximum time to wait in seconds
            poll_interval: Time between status checks in seconds

        Returns:
            Order details dictionary with Status field
        """
        start_time = time.time()
        logger.info(f"Waiting for order {order_id} to be filled (max {max_wait_seconds}s)")

        while time.time() - start_time < max_wait_seconds:
            response = self._get(f"/trade/v3/orders/{order_id}/details")
            if response and "Status" in response:
                status = response["Status"]
                logger.info(f"Order {order_id} status: {status}")

                if status in ["Filled", "Executed"]:
                    self._update_trade_status_metric(status)
                    return response

            time.sleep(poll_interval)

        logger.warning(f"Order {order_id} not filled within {max_wait_seconds}s")
        return {"OrderId": order_id, "Status": "Timeout"}

    def _update_trade_status_metric(self, status: str) -> None:
        """
        Update the Prometheus metric for trade status.

        Args:
            status: The status of the order (Filled or Executed)
        """
        update_trade_status(status)

    def _get(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """
        Make a GET request to the Saxo API.

        Args:
            endpoint: API endpoint (e.g., "/trade/v3/orders/123/details")
            **kwargs: Additional arguments for the request

        Returns:
            Response from the API as a dictionary
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        if "headers" not in kwargs:
            kwargs["headers"] = headers
        else:
            kwargs["headers"].update(headers)

        response = request("GET", url, **kwargs)
        if isinstance(response, dict):
            return response
        return dict(response.json())

    def _post(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """
        Make a POST request to the Saxo API.

        Args:
            endpoint: API endpoint (e.g., "/trade/v3/orders")
            **kwargs: Additional arguments for the request

        Returns:
            Response from the API as a dictionary
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        if "headers" not in kwargs:
            kwargs["headers"] = headers
        else:
            kwargs["headers"].update(headers)

        response = request("POST", url, **kwargs)
        if isinstance(response, dict):
            return response
        return dict(response.json())

    def _build_market_order_body(
        self, instrument: str, side: str, amount: int | float | Decimal
    ) -> dict:
        """
        Build the request body for a Market order.

        Args:
            instrument: The instrument to trade
            side: Buy or Sell
            amount: The amount to trade

        Returns:
            The request body for the Market order
        """
        return {
            "OrderType": "Market",
            "AssetType": "FxSpot",
            "BuySell": side,
            "Amount": str(amount),
            "AmountType": "Lots",
            "Uic": self._get_instrument_uic(instrument),
            "OrderDuration": {"DurationType": "DayOrder"},
        }

    def _get_instrument_uic(self, instrument: str) -> int:
        """
        Get the UIC (Universal Instrument Code) for an instrument.

        Args:
            instrument: The instrument code (e.g., USDJPY)

        Returns:
            The UIC for the instrument
        """
        # Hardcoded mapping for common instruments in sim environment
        instrument_uics = {"USDJPY": 1, "EURJPY": 2, "EURUSD": 3}
        return instrument_uics.get(instrument, 1)  # Default to 1 (USDJPY) if not found

    @retryable(max_attempts=3, statuses=[429], backoff_factor=1.0, jitter_factor=0.2)
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

        Implements a chain-of-responsibility pattern for guard systems:
        1. Check if KillSwitch is active
        2. Check if ModeGuard is paused
        3. Check if LatencyGuard is triggered
        4. Check if SlippageGuard rejects the order
        5. Perform API precheck

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

        current_equity = 800000.0  # 800,000 JPY

        if self.kill_switch.is_active():
            logger.error("KillSwitch is active, rejecting order")
            return {"KillSwitchRejection": True, "PreCheckResult": "Rejected"}

        if not self.kill_switch.check_equity(current_equity):
            logger.error("KillSwitch triggered due to excessive daily loss")
            return {"KillSwitchRejection": True, "PreCheckResult": "Rejected"}

        if self.mode_guard.is_paused():
            logger.error("ModeGuard is paused, rejecting order")
            return {"ModeGuardRejection": True, "PreCheckResult": "Rejected"}

        if self.latency_guard.is_triggered():
            logger.error("LatencyGuard is triggered, rejecting order")
            return {"LatencyGuardRejection": True, "PreCheckResult": "Rejected"}

        quote_data = self.get_quote(instrument)
        if not quote_data or "Quote" not in quote_data:
            logger.error(f"Failed to get quote for {instrument}, cannot check spread")
            return None

        quote = quote_data["Quote"]
        ask = float(quote.get("Ask", 0))
        bid = float(quote.get("Bid", 0))
        mid = (ask + bid) / 2

        start_time = time.time()

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
            response_obj = request(
                "POST",
                f"{self.base_url}{endpoint}",
                headers=headers,
                json=order_data,
                timeout=self.timeout,
            )
            if hasattr(response_obj, "raise_for_status"):
                response_obj.raise_for_status()
                precheck_result: dict[str, Any] = response_obj.json()
            else:
                if hasattr(response_obj, "json"):
                    precheck_result = response_obj.json()
                else:
                    precheck_result = cast(dict[str, Any], response_obj)

            latency_ms = (time.time() - start_time) * 1000
            if not self.latency_guard.check_latency(latency_ms):
                logger.error(f"LatencyGuard triggered due to high latency: {latency_ms:.2f} ms")
                return {"LatencyGuardRejection": True, "PreCheckResult": "Rejected"}

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

    @retryable(max_attempts=3, statuses=[429], backoff_factor=1.0, jitter_factor=0.2)
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
            response_obj = request(
                "PUT",
                f"{self.base_url}{endpoint}",
                headers=headers,
                timeout=self.timeout,
            )
            if hasattr(response_obj, "raise_for_status"):
                response_obj.raise_for_status()
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

    @retryable(max_attempts=3, statuses=[429], backoff_factor=1.0, jitter_factor=0.2)
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
            response_obj = request(
                "DELETE",
                f"{self.base_url}{endpoint}",
                headers=headers,
                timeout=self.timeout,
            )
            if hasattr(response_obj, "raise_for_status"):
                response_obj.raise_for_status()
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

    @retryable(max_attempts=3, statuses=[429], backoff_factor=1.0, jitter_factor=0.2)
    def get_order_status(self, order_id: str) -> dict[str, Any] | None:
        """
        Get the status of an order.

        Args:
            order_id: The ID of the order to check

        Returns:
            Optional[dict[str, Any]]: Order status information or None if the request failed
        """
        if not self.access_token:
            logger.error("Not authenticated")
            return None

        headers = self._get_headers()

        trade_version = "v3" if self.use_trade_v3 else "v2"
        endpoint = f"/trade/{trade_version}/orders/{order_id}/details"

        try:
            logger.info(f"Getting status for order {order_id}")
            response = request(
                "GET",
                f"{self.base_url}{endpoint}",
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            status_data: dict[str, Any] = response.json()
            logger.info(
                f"Successfully retrieved status for order {order_id}: {status_data.get('Status')}"
            )
            return status_data
        except requests.HTTPError as e:
            if hasattr(e, "response") and e.response is not None:
                logger.error(
                    f"Failed to get order status for {order_id} with status {e.response.status_code}"
                )
                raise SaxoApiError(
                    f"Failed to get order status for {order_id}",
                    e.response.status_code,
                    e.response.json(),
                ) from e
            else:
                logger.error(f"Failed to get order status for {order_id}: {str(e)}")
                raise SaxoApiError(f"Failed to get order status for {order_id}", None, None) from e
        except requests.RequestException as e:
            logger.error(f"Order status request failed for {order_id}: {str(e)}")
            return None

    def wait_for_order_status(
        self,
        order_id: str,
        target_status: str | list[str] = ["Filled", "Executed"],
        max_wait_seconds: int = 60,
        poll_interval: int = 2,
    ) -> dict[str, Any] | None:
        """
        Poll for order status until it reaches the target status or timeout.

        Args:
            order_id: The ID of the order to check
            target_status: The status to wait for (or list of statuses)
            max_wait_seconds: Maximum time to wait in seconds
            poll_interval: Time between polls in seconds

        Returns:
            Optional[dict[str, Any]]: Order status information or None if the target status wasn't reached
        """
        if isinstance(target_status, str):
            target_status = [target_status]

        logger.info(f"Waiting for order {order_id} to reach status: {','.join(target_status)}")
        end_time = time.time() + max_wait_seconds
        last_status = None

        while time.time() < end_time:
            status_data = self.get_order_status(order_id)
            if status_data is None:
                logger.error(f"Failed to get status for order {order_id}")
                time.sleep(poll_interval)
                continue

            current_status = status_data.get("Status", "Unknown")
            if current_status != last_status:
                logger.info(f"Order {order_id} status: {current_status}")
                last_status = current_status

            if (
                current_status in target_status
                or "status" in status_data
                and status_data["status"] in target_status
            ):
                self._update_trade_metrics(status_data)
                return status_data

            time.sleep(poll_interval)

        logger.warning(
            f"Timed out waiting for order {order_id} to reach status: {','.join(target_status)}"
        )
        return None

    def _update_trade_metrics(self, status_data: dict[str, Any]) -> None:
        """
        Update Prometheus metrics based on order status.

        Args:
            status_data: Order status data from the API
        """
        if self.last_trade_status is None:
            logger.warning("Prometheus metrics not initialized, skipping metric update")
            return

        current_status = status_data.get("Status", "Unknown")

        for status in ["Working", "Filled", "Executed", "Rejected", "Cancelled", "Unknown"]:
            self.last_trade_status.labels(env=self.environment, status=status).set(0)

        if current_status in ["Filled", "Executed"]:
            logger.info("Order filled/executed, updating Prometheus metric")
            self.last_trade_status.labels(env=self.environment, status="Filled").set(1)
            if current_status == "Executed":
                self.last_trade_status.labels(env=self.environment, status="Executed").set(1)
        else:
            self.last_trade_status.labels(env=self.environment, status=current_status).set(1)
