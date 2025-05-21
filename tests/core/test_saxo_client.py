"""
Unit tests for the SaxoClient class.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.common.exceptions import OrderPollingTimeoutError, SaxoApiError
from src.core.saxo_client import SaxoClient


class TestSaxoClient:
    """Test suite for the SaxoClient class."""

    def setup_method(self) -> None:
        """Set up test environment before each test method."""
        os.environ["LIVE_CLIENT_ID"] = "test_client_id"
        os.environ["LIVE_CLIENT_SECRET"] = "test_secret"  # nosec: B105 # Testing value
        os.environ["LIVE_REFRESH_TOKEN"] = "test_token"  # nosec: B105 # Testing value
        os.environ["LIVE_ACCOUNT_KEY"] = "test_account_key"
        os.environ["USE_TRADE_V3"] = "false"

        self.client = SaxoClient(environment="live")

    def teardown_method(self) -> None:
        """Clean up after each test method."""
        for key in [
            "LIVE_CLIENT_ID",
            "LIVE_CLIENT_SECRET",
            "LIVE_REFRESH_TOKEN",
            "LIVE_ACCOUNT_KEY",
            "USE_TRADE_V3",
        ]:
            if key in os.environ:
                del os.environ[key]

    def test_init(self) -> None:
        """Test client initialization."""
        assert self.client.environment == "live"  # nosec: B101 # pytest assertion
        assert (
            self.client.base_url == "https://gateway.saxobank.com/openapi"
        )  # nosec: B101 # pytest assertion
        assert self.client.client_id == "test_client_id"  # nosec: B101 # pytest assertion
        assert self.client.client_secret == "test_secret"  # nosec: B101 # pytest assertion
        assert self.client.refresh_token == "test_token"  # nosec: B101 # pytest assertion
        assert self.client.account_key == "test_account_key"  # nosec: B101 # pytest assertion
        assert self.client.access_token is None  # nosec: B101 # pytest assertion
        assert self.client.token_expiry is None  # nosec: B101 # pytest assertion
        assert self.client.timeout == 5  # nosec: B101 # pytest assertion
        assert self.client.use_trade_v3 is False  # nosec: B101 # pytest assertion

    def test_init_sim_environment(self) -> None:
        """Test client initialization with simulation environment."""
        client = SaxoClient(environment="sim")
        assert client.environment == "sim"  # nosec: B101 # pytest assertion
        assert (
            client.base_url == "https://gateway.saxobank.com/sim/openapi"
        )  # nosec: B101 # pytest assertion

    def test_init_with_trade_v3(self) -> None:
        """Test client initialization with USE_TRADE_V3=true."""
        os.environ["USE_TRADE_V3"] = "true"
        client = SaxoClient(environment="live")
        assert client.use_trade_v3 is True  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.request")
    def test_authenticate_success(self, mock_request: MagicMock) -> None:
        """Test successful authentication."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token"
        }  # nosec: B105 # Testing value
        mock_request.return_value = mock_response

        result = self.client.authenticate()

        assert result is True  # nosec: B101 # pytest assertion
        assert self.client.access_token == "test_token"  # nosec: B101 # pytest assertion
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "POST"  # nosec: B101 # pytest assertion
        assert (
            args[1] == "https://gateway.saxobank.com/openapi/token"
        )  # nosec: B101 # pytest assertion
        assert kwargs["data"]["grant_type"] == "refresh_token"  # nosec: B101 # pytest assertion
        assert kwargs["data"]["refresh_token"] == "test_token"  # nosec: B101 # pytest assertion
        assert kwargs["data"]["client_id"] == "test_client_id"  # nosec: B101 # pytest assertion
        assert kwargs["data"]["client_secret"] == "test_secret"  # nosec: B101 # pytest assertion
        assert kwargs["timeout"] == 5  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.request")
    def test_authenticate_retry(self, mock_request: MagicMock) -> None:
        """Test authentication retry on failure."""
        mock_error_response = MagicMock()
        mock_error_response.status_code = 503
        mock_error_response.raise_for_status.side_effect = requests.HTTPError("Service Unavailable")

        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {"access_token": "test_token"}

        mock_request.side_effect = [
            requests.HTTPError("Service Unavailable"),
            mock_success_response,
        ]

        with patch("time.sleep") as mock_sleep:  # Skip actual sleeping
            result = self.client.authenticate()

        assert result is True  # nosec: B101 # pytest assertion
        assert self.client.access_token == "test_token"  # nosec: B101 # pytest assertion
        assert mock_request.call_count == 2  # nosec: B101 # pytest assertion
        assert mock_sleep.called  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.request")
    def test_authenticate_failure(self, mock_request: MagicMock) -> None:
        """Test authentication failure."""
        mock_request.side_effect = requests.RequestException("Connection error")

        result = self.client.authenticate()

        assert result is False  # nosec: B101 # pytest assertion
        assert self.client.access_token is None  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.request")
    def test_authenticate_http_error_without_response(self, mock_request: MagicMock) -> None:
        """Test authentication with HTTP error but no response attribute."""
        error = requests.HTTPError("HTTP Error")
        mock_request.side_effect = error

        with pytest.raises(SaxoApiError) as excinfo:
            self.client.authenticate()

        assert "Authentication failed" in str(excinfo.value)  # nosec: B101 # pytest assertion
        assert excinfo.value.status_code is None  # nosec: B101 # pytest assertion
        assert excinfo.value.response_body is None  # nosec: B101 # pytest assertion

    def test_authenticate_missing_credentials(self) -> None:
        """Test authentication failure due to missing credentials."""
        self.client.client_id = None
        self.client.client_secret = None
        self.client.refresh_token = None

        result = self.client.authenticate()

        assert result is False  # nosec: B101 # pytest assertion

    def test_get_headers_not_authenticated(self) -> None:
        """Test getting headers when not authenticated."""
        with pytest.raises(ValueError):
            self.client._get_headers()

    def test_get_headers_authenticated(self) -> None:
        """Test getting headers when authenticated."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value
        headers = self.client._get_headers()
        assert headers == {"Authorization": "Bearer test_token"}  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.request")
    def test_get_quote_success(self, mock_request: MagicMock) -> None:
        """Test successful quote retrieval."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Quote": {"Ask": 1.1234, "Bid": 1.1232, "Mid": 1.1233}}
        mock_request.return_value = mock_response

        result = self.client.get_quote("EURUSD")

        assert result == {
            "Quote": {"Ask": 1.1234, "Bid": 1.1232, "Mid": 1.1233}
        }  # nosec: B101 # pytest assertion
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "GET"  # nosec: B101 # pytest assertion
        assert (
            args[1] == "https://gateway.saxobank.com/openapi/trade/v1/prices/quotes"
        )  # nosec: B101 # pytest assertion
        assert kwargs["params"]["AssetType"] == "FxSpot"  # nosec: B101 # pytest assertion
        assert kwargs["params"]["Uic"] == "EURUSD"  # nosec: B101 # pytest assertion
        assert (
            kwargs["headers"]["Authorization"] == "Bearer test_token"
        )  # nosec: B101 # pytest assertion
        assert kwargs["timeout"] == 5  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.request")
    def test_get_quote_retry(self, mock_request: MagicMock) -> None:
        """Test quote retrieval retry on failure."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value

        mock_error_response = MagicMock()
        mock_error_response.status_code = 429
        mock_error_response.raise_for_status.side_effect = requests.HTTPError("Too Many Requests")

        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {
            "Quote": {"Ask": 1.1234, "Bid": 1.1232, "Mid": 1.1233}
        }

        mock_request.side_effect = [
            requests.HTTPError("Too Many Requests"),
            mock_success_response,
        ]

        with patch("time.sleep") as mock_sleep:  # Skip actual sleeping
            result = self.client.get_quote("EURUSD")

        assert result == {
            "Quote": {"Ask": 1.1234, "Bid": 1.1232, "Mid": 1.1233}
        }  # nosec: B101 # pytest assertion
        assert mock_request.call_count == 2  # nosec: B101 # pytest assertion
        assert mock_sleep.called  # nosec: B101 # pytest assertion

    def test_get_quote_missing_credentials(self) -> None:
        """Test quote retrieval failure due to missing credentials."""
        self.client.access_token = None

        result = self.client.get_quote("EURUSD")

        assert result is None  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.request")
    def test_get_quote_failure(self, mock_request: MagicMock) -> None:
        """Test quote retrieval failure due to HTTP error."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value

        mock_request.side_effect = requests.RequestException("Connection error")

        result = self.client.get_quote("EURUSD")

        assert result is None  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.request")
    def test_get_quote_http_error_without_response(self, mock_request: MagicMock) -> None:
        """Test quote retrieval with HTTP error but no response attribute."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value

        error = requests.HTTPError("HTTP Error")
        mock_request.side_effect = error

        with pytest.raises(SaxoApiError) as excinfo:
            self.client.get_quote("EURUSD")

        assert "Failed to get quote for EURUSD" in str(
            excinfo.value
        )  # nosec: B101 # pytest assertion
        assert excinfo.value.status_code is None  # nosec: B101 # pytest assertion
        assert excinfo.value.response_body is None  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.SaxoClient._precheck_order")
    @patch("src.core.saxo_client.request")
    def test_place_order_success(self, mock_request: MagicMock, mock_precheck: MagicMock) -> None:
        """Test successful order placement."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value
        self.client.account_key = "test_account_key"

        mock_precheck.return_value = {"PreCheckResult": "OK"}

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"OrderId": "123456"}
        mock_request.return_value = mock_response

        result = self.client.place_order(
            instrument="EURUSD", order_type="Market", side="Buy", amount=1000
        )

        assert result == {"OrderId": "123456"}  # nosec: B101 # pytest assertion
        mock_precheck.assert_called_once()
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "POST"  # nosec: B101 # pytest assertion
        assert (
            args[1] == "https://gateway.saxobank.com/openapi/trade/v2/orders"
        )  # nosec: B101 # pytest assertion
        assert kwargs["json"]["AccountKey"] == "test_account_key"  # nosec: B101 # pytest assertion
        assert kwargs["json"]["AssetType"] == "FxSpot"  # nosec: B101 # pytest assertion
        assert kwargs["json"]["Amount"] == "1000"  # nosec: B101 # pytest assertion
        assert kwargs["json"]["BuySell"] == "Buy"  # nosec: B101 # pytest assertion
        assert kwargs["json"]["OrderType"] == "Market"  # nosec: B101 # pytest assertion
        assert kwargs["json"]["Uic"] == "EURUSD"  # nosec: B101 # pytest assertion
        assert (
            kwargs["headers"]["Authorization"] == "Bearer test_token"
        )  # nosec: B101 # pytest assertion
        assert kwargs["timeout"] == 5  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.SaxoClient._precheck_order")
    @patch("src.core.saxo_client.SaxoClient._accept_disclaimer")
    @patch("src.core.saxo_client.request")
    def test_place_order_with_disclaimers(
        self, mock_request: MagicMock, mock_accept: MagicMock, mock_precheck: MagicMock
    ) -> None:
        """Test order placement with disclaimers."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value
        self.client.account_key = "test_account_key"

        mock_precheck.side_effect = [
            {"BlockingDisclaimers": [{"Id": "disclaimer1"}]},
            {"PreCheckResult": "OK"},
        ]

        mock_accept.return_value = True

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"OrderId": "123456"}
        mock_request.return_value = mock_response

        result = self.client.place_order(
            instrument="EURUSD", order_type="Market", side="Buy", amount=1000
        )

        assert result == {"OrderId": "123456"}  # nosec: B101 # pytest assertion
        assert mock_precheck.call_count == 2  # nosec: B101 # pytest assertion
        mock_accept.assert_called_once_with("disclaimer1")
        mock_request.assert_called_once()

    @patch("src.core.saxo_client.SaxoClient._precheck_order")
    def test_place_order_precheck_failure(self, mock_precheck: MagicMock) -> None:
        """Test order placement failure due to precheck failure."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value
        self.client.account_key = "test_account_key"

        mock_precheck.return_value = None

        result = self.client.place_order(
            instrument="EURUSD", order_type="Market", side="Buy", amount=1000
        )

        assert result is None  # nosec: B101 # pytest assertion
        mock_precheck.assert_called_once()

    @patch("src.core.saxo_client.SaxoClient._precheck_order")
    @patch("src.core.saxo_client.SaxoClient._accept_disclaimer")
    def test_place_order_disclaimer_failure(
        self, mock_accept: MagicMock, mock_precheck: MagicMock
    ) -> None:
        """Test order placement failure due to disclaimer acceptance failure."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value
        self.client.account_key = "test_account_key"

        mock_precheck.return_value = {"BlockingDisclaimers": [{"Id": "disclaimer1"}]}

        mock_accept.return_value = False

        result = self.client.place_order(
            instrument="EURUSD", order_type="Market", side="Buy", amount=1000
        )

        assert result is None  # nosec: B101 # pytest assertion
        mock_precheck.assert_called_once()
        mock_accept.assert_called_once_with("disclaimer1")

    def test_place_order_missing_credentials(self) -> None:
        """Test order placement failure due to missing credentials."""
        self.client.access_token = None

        result = self.client.place_order(
            instrument="EURUSD", order_type="Market", side="Buy", amount=1000
        )

        assert result is None  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.request")
    def test_place_order_http_error_without_response(self, mock_request: MagicMock) -> None:
        """Test order placement with HTTP error but no response attribute."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value
        self.client.account_key = "test_account_key"

        with patch("src.core.saxo_client.SaxoClient._precheck_order") as mock_precheck:
            mock_precheck.return_value = {"PreCheckResult": "OK"}

            error = requests.HTTPError("HTTP Error")
            mock_request.side_effect = error

            with pytest.raises(SaxoApiError) as excinfo:
                self.client.place_order(
                    instrument="EURUSD", order_type="Market", side="Buy", amount=1000
                )

            assert "Failed to place order" in str(excinfo.value)  # nosec: B101 # pytest assertion
            assert excinfo.value.status_code is None  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.request")
    def test_get_order_status(self, mock_request: MagicMock) -> None:
        """Test getting order status."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Status": "Filled", "OrderId": "123"}
        mock_request.return_value = mock_response

        self.client.access_token = "test_token"  # nosec: B105 # Testing value

        result = self.client.get_order_status("123")

        assert result is not None  # nosec: B101 # pytest assertion
        assert result["Status"] == "Filled"  # nosec: B101 # pytest assertion
        assert result["OrderId"] == "123"  # nosec: B101 # pytest assertion

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "GET"  # nosec: B101 # pytest assertion
        assert "orders/123/details" in args[1]  # nosec: B101 # pytest assertion

    def test_get_order_status_not_authenticated(self) -> None:
        """Test getting order status when not authenticated."""
        self.client.access_token = None

        result = self.client.get_order_status("123")

        assert result is None  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.request")
    def test_get_order_status_request_failure(self, mock_request: MagicMock) -> None:
        """Test getting order status when the request fails."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value

        mock_request.side_effect = requests.RequestException("Failed")

        result = self.client.get_order_status("123")

        assert result is None  # nosec: B101 # pytest assertion

    @patch("time.sleep", return_value=None)
    @patch("time.time", side_effect=[0, 10, 20, 30, 40, 50, 60])
    @patch("src.core.saxo_client.SaxoClient.get_order_status")
    def test_wait_for_order_status_success(
        self, mock_get_status: MagicMock, mock_time: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Test waiting for order status to reach a target status."""
        mock_get_status.side_effect = [{"Status": "Working"}, {"Status": "Filled"}]

        result = self.client.wait_for_order_status("123", target_status="Filled")

        assert result is not None  # nosec: B101 # pytest assertion
        assert result["Status"] == "Filled"  # nosec: B101 # pytest assertion

        assert mock_get_status.call_count == 2  # nosec: B101 # pytest assertion

    @patch("time.sleep", return_value=None)
    @patch("time.time", side_effect=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120])
    @patch("src.core.saxo_client.SaxoClient.get_order_status")
    def test_wait_for_order_status_timeout(
        self, mock_get_status: MagicMock, mock_time: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Test waiting for order status with a timeout."""
        mock_get_status.return_value = {"Status": "Working"}

        with pytest.raises(OrderPollingTimeoutError) as excinfo:
            self.client.wait_for_order_status(
                "123", target_status="Filled", max_wait_seconds=50
            )

        assert "Order 123 polling timed out" in str(excinfo.value)  # nosec: B101 # pytest assertion
        assert mock_get_status.call_count > 1  # nosec: B101 # pytest assertion

    @patch("time.sleep", return_value=None)
    @patch("time.time", side_effect=[0, 10, 20, 30, 40, 50, 60])
    @patch("src.core.saxo_client.SaxoClient.get_order_status")
    def test_wait_for_order_status_multiple_targets(
        self, mock_get_status: MagicMock, mock_time: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Test waiting for order status with multiple target statuses."""
        mock_get_status.side_effect = [{"Status": "Working"}, {"Status": "Executed"}]

        result = self.client.wait_for_order_status("123", target_status=["Filled", "Executed"])

        assert result is not None  # nosec: B101 # pytest assertion
        assert result["Status"] == "Executed"  # nosec: B101 # pytest assertion

    @patch("time.sleep", return_value=None)
    @patch("src.core.saxo_client.SaxoClient.get_order_status")
    def test_wait_for_order_status_get_status_none(
        self, mock_get_status: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Test waiting for order status when get_order_status returns None."""
        mock_get_status.return_value = None

        with pytest.raises(OrderPollingTimeoutError) as excinfo:
            self.client.wait_for_order_status(
                "123", target_status="Filled", max_wait_seconds=5
            )

        assert "Order 123 polling timed out" in str(excinfo.value)  # nosec: B101 # pytest assertion
        assert mock_get_status.call_count > 1  # nosec: B101 # pytest assertion

    @patch("time.sleep", return_value=None)
    @patch("src.core.saxo_client.SaxoClient.get_order_status")
    def test_wait_for_order_status_timeout_with_status(
        self, mock_get_status: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Test waiting for order status when the order never reaches the target status."""
        mock_get_status.return_value = {"Status": "Working"}

        with pytest.raises(OrderPollingTimeoutError) as excinfo:
            self.client.wait_for_order_status(
                "123", target_status="Filled", max_wait_seconds=5
            )

        assert "Order 123 polling timed out" in str(excinfo.value)  # nosec: B101 # pytest assertion
        assert "Working" in str(excinfo.value)  # nosec: B101 # pytest assertion
        assert mock_get_status.call_count > 1  # nosec: B101 # pytest assertion

    @patch("time.sleep", return_value=None)
    @patch("src.core.saxo_client.SaxoClient.get_order_status")
    def test_wait_for_order_status_with_status_key(
        self, mock_get_status: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Test waiting for order status when the API returns status in lowercase key."""
        mock_get_status.return_value = {"status": "Filled"}

        result = self.client.wait_for_order_status("123", target_status="Filled")

        assert result is not None  # nosec: B101 # pytest assertion
        assert result["status"] == "Filled"  # nosec: B101 # pytest assertion

    @patch("time.sleep", return_value=None)
    @patch("src.core.saxo_client.SaxoClient.get_order_status")
    def test_wait_for_order_status_string_target(
        self, mock_get_status: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Test waiting for order status with a string target instead of a list."""
        mock_get_status.return_value = {"Status": "Filled"}

        result = self.client.wait_for_order_status("123", target_status="Filled")

        assert result is not None  # nosec: B101 # pytest assertion
        assert result["Status"] == "Filled"  # nosec: B101 # pytest assertion

    def test_update_trade_metrics_filled(self) -> None:
        """Test updating trade metrics when an order is filled."""
        self.client.last_trade_status = MagicMock()

        self.client._update_trade_metrics({"Status": "Filled"})

        assert (
            self.client.last_trade_status.labels.call_count >= 1
        )  # nosec: B101 # pytest assertion
        self.client.last_trade_status.labels.assert_any_call(
            env=self.client.environment, status="Filled"
        )

    def test_update_trade_metrics_not_initialized(self) -> None:
        """Test updating trade metrics when Prometheus metrics are not initialized."""
        from typing import cast

        self.client.last_trade_status = cast(None, None)  # type: ignore # Intentionally set to None for testing

        self.client._update_trade_metrics({"Status": "Filled"})

    def test_update_trade_metrics_executed(self) -> None:
        """Test updating trade metrics when an order is executed."""
        self.client.last_trade_status = MagicMock()

        self.client._update_trade_metrics({"Status": "Executed"})

        assert (
            self.client.last_trade_status.labels.call_count >= 1
        )  # nosec: B101 # pytest assertion
        self.client.last_trade_status.labels.assert_any_call(
            env=self.client.environment, status="Filled"
        )
        self.client.last_trade_status.labels.assert_any_call(
            env=self.client.environment, status="Executed"
        )

    def test_update_trade_metrics_other_status(self) -> None:
        """Test updating trade metrics with a status other than Filled/Executed."""
        self.client.last_trade_status = MagicMock()

        self.client._update_trade_metrics({"Status": "Working"})

        assert (
            self.client.last_trade_status.labels.call_count >= 1
        )  # nosec: B101 # pytest assertion
        self.client.last_trade_status.labels.assert_any_call(
            env=self.client.environment, status="Working"
        )

    @patch("src.core.saxo_client.request")
    @patch("src.core.saxo_client.SaxoClient.get_quote")
    def test_precheck_order_success(
        self, mock_get_quote: MagicMock, mock_request: MagicMock
    ) -> None:
        """Test successful order precheck."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value
        self.client.account_key = "test_account_key"

        mock_get_quote.return_value = {"Quote": {"Ask": 1.1235, "Bid": 1.1225}}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"PreCheckResult": "OK"}
        mock_request.return_value = mock_response

        result = self.client._precheck_order(
            instrument="EURUSD", order_type="Market", side="Buy", amount=1000
        )

        assert result == {"PreCheckResult": "OK"}  # nosec: B101 # pytest assertion
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "POST"  # nosec: B101 # pytest assertion
        assert (
            args[1] == "https://gateway.saxobank.com/openapi/trade/v2/orders/precheck"
        )  # nosec: B101 # pytest assertion
        assert kwargs["json"]["AccountKey"] == "test_account_key"  # nosec: B101 # pytest assertion
        assert kwargs["json"]["AssetType"] == "FxSpot"  # nosec: B101 # pytest assertion
        assert kwargs["json"]["Amount"] == "1000"  # nosec: B101 # pytest assertion
        assert kwargs["json"]["BuySell"] == "Buy"  # nosec: B101 # pytest assertion
        assert kwargs["json"]["OrderType"] == "Market"  # nosec: B101 # pytest assertion
        assert kwargs["json"]["Uic"] == "EURUSD"  # nosec: B101 # pytest assertion
        assert (
            kwargs["headers"]["Authorization"] == "Bearer test_token"
        )  # nosec: B101 # pytest assertion
        assert kwargs["timeout"] == 5  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.request")
    @patch("src.core.saxo_client.SaxoClient.get_quote")
    def test_precheck_order_with_price(
        self, mock_get_quote: MagicMock, mock_request: MagicMock
    ) -> None:
        """Test order precheck with price for limit order."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value
        self.client.account_key = "test_account_key"

        mock_get_quote.return_value = {"Quote": {"Ask": 1.1235, "Bid": 1.1225}}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"PreCheckResult": "OK"}
        mock_request.return_value = mock_response

        result = self.client._precheck_order(
            instrument="EURUSD", order_type="Limit", side="Buy", amount=1000, price=1.1234
        )

        assert result == {"PreCheckResult": "OK"}  # nosec: B101 # pytest assertion
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert kwargs["json"]["Price"] == "1.1234"  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.request")
    @patch("src.core.saxo_client.SaxoClient.get_quote")
    def test_precheck_order_failure(
        self, mock_get_quote: MagicMock, mock_request: MagicMock
    ) -> None:
        """Test order precheck failure due to HTTP error."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value
        self.client.account_key = "test_account_key"

        mock_get_quote.return_value = {"Quote": {"Ask": 1.1235, "Bid": 1.1225}}

        mock_request.side_effect = requests.RequestException("Connection error")

        result = self.client._precheck_order(
            instrument="EURUSD", order_type="Market", side="Buy", amount=1000
        )

        assert result is None  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.request")
    @patch("src.core.saxo_client.SaxoClient.get_quote")
    def test_precheck_order_http_error_without_response(
        self, mock_get_quote: MagicMock, mock_request: MagicMock
    ) -> None:
        """Test order precheck with HTTP error but no response attribute."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value
        self.client.account_key = "test_account_key"

        mock_get_quote.return_value = {"Quote": {"Ask": 1.1235, "Bid": 1.1225}}

        error = requests.HTTPError("HTTP Error")
        mock_request.side_effect = error

        with pytest.raises(SaxoApiError) as excinfo:
            self.client._precheck_order(
                instrument="EURUSD", order_type="Market", side="Buy", amount=1000
            )

        assert "Order precheck failed" in str(excinfo.value)  # nosec: B101 # pytest assertion
        assert excinfo.value.status_code is None  # nosec: B101 # pytest assertion
        assert excinfo.value.response_body is None  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.request")
    def test_accept_disclaimer_success(self, mock_request: MagicMock) -> None:
        """Test successful disclaimer acceptance."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        result = self.client._accept_disclaimer("disclaimer1")

        assert result is True  # nosec: B101 # pytest assertion
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "PUT"  # nosec: B101 # pytest assertion
        assert (
            args[1]
            == "https://gateway.saxobank.com/openapi/trade/v1/disclaimers/disclaimer1/accept"
        )  # nosec: B101 # pytest assertion
        assert (
            kwargs["headers"]["Authorization"] == "Bearer test_token"
        )  # nosec: B101 # pytest assertion
        assert kwargs["timeout"] == 5  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.request")
    def test_accept_disclaimer_failure(self, mock_request: MagicMock) -> None:
        """Test disclaimer acceptance failure due to HTTP error."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value

        mock_request.side_effect = requests.RequestException("Connection error")

        result = self.client._accept_disclaimer("disclaimer1")

        assert result is False  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.request")
    def test_accept_disclaimer_http_error_without_response(self, mock_request: MagicMock) -> None:
        """Test disclaimer acceptance with HTTP error but no response attribute."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value

        error = requests.HTTPError("HTTP Error")
        mock_request.side_effect = error

        with pytest.raises(SaxoApiError) as excinfo:
            self.client._accept_disclaimer("disclaimer1")

        assert "Failed to accept disclaimer disclaimer1" in str(
            excinfo.value
        )  # nosec: B101 # pytest assertion
        assert excinfo.value.status_code is None  # nosec: B101 # pytest assertion
        assert excinfo.value.response_body is None  # nosec: B101 # pytest assertion

    def test_accept_disclaimer_missing_credentials(self) -> None:
        """Test disclaimer acceptance failure due to missing credentials."""
        self.client.access_token = None

        result = self.client._accept_disclaimer("disclaimer1")

        assert result is False  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.request")
    def test_cancel_order_success(self, mock_request: MagicMock) -> None:
        """Test successful order cancellation."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        result = self.client.cancel_order("123456")

        assert result is True  # nosec: B101 # pytest assertion
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "DELETE"  # nosec: B101 # pytest assertion
        assert (
            args[1] == "https://gateway.saxobank.com/openapi/trade/v2/orders/123456"
        )  # nosec: B101 # pytest assertion
        assert (
            kwargs["headers"]["Authorization"] == "Bearer test_token"
        )  # nosec: B101 # pytest assertion
        assert kwargs["timeout"] == 5  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.request")
    def test_cancel_order_retry(self, mock_request: MagicMock) -> None:
        """Test order cancellation retry on failure."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value

        mock_error_response = MagicMock()
        mock_error_response.status_code = 502
        mock_error_response.raise_for_status.side_effect = requests.HTTPError("Bad Gateway")

        mock_success_response = MagicMock()
        mock_success_response.status_code = 200

        mock_request.side_effect = [
            requests.HTTPError("Bad Gateway"),
            mock_success_response,
        ]

        with patch("time.sleep") as mock_sleep:  # Skip actual sleeping
            result = self.client.cancel_order("123456")

        assert result is True  # nosec: B101 # pytest assertion
        assert mock_request.call_count == 2  # nosec: B101 # pytest assertion
        assert mock_sleep.called  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.request")
    def test_cancel_order_failure(self, mock_request: MagicMock) -> None:
        """Test order cancellation failure due to HTTP error."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value

        mock_request.side_effect = requests.RequestException("Connection error")

        result = self.client.cancel_order("123456")

        assert result is False  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.request")
    def test_cancel_order_http_error_without_response(self, mock_request: MagicMock) -> None:
        """Test order cancellation with HTTP error but no response attribute."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value

        error = requests.HTTPError("HTTP Error")
        mock_request.side_effect = error

        with pytest.raises(SaxoApiError) as excinfo:
            self.client.cancel_order("123456")

        assert "Failed to cancel order 123456" in str(
            excinfo.value
        )  # nosec: B101 # pytest assertion
        assert excinfo.value.status_code is None  # nosec: B101 # pytest assertion
        assert excinfo.value.response_body is None  # nosec: B101 # pytest assertion

    def test_cancel_order_missing_credentials(self) -> None:
        """Test order cancellation failure due to missing credentials."""
        self.client.access_token = None

        result = self.client.cancel_order("123456")

        assert result is False  # nosec: B101 # pytest assertion

    def test_use_trade_v3_endpoint(self) -> None:
        """Test using v3 trade endpoints when USE_TRADE_V3=true."""
        os.environ["USE_TRADE_V3"] = "true"
        client = SaxoClient(environment="live")
        client.access_token = "test_token"  # nosec: B105 # Testing value
        client.account_key = "test_account_key"

        with patch("src.core.saxo_client.request") as mock_request, patch(
            "src.core.saxo_client.SaxoClient.get_quote"
        ) as mock_get_quote:
            mock_get_quote.return_value = {"Quote": {"Ask": 1.1235, "Bid": 1.1225}}

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"PreCheckResult": "OK"}
            mock_request.return_value = mock_response

            client._precheck_order(
                instrument="EURUSD", order_type="Market", side="Buy", amount=1000
            )

            args, kwargs = mock_request.call_args
            assert args[0] == "POST"  # nosec: B101 # pytest assertion
            assert (
                args[1] == "https://gateway.saxobank.com/openapi/trade/v3/orders/precheck"
            )  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.SaxoClient._precheck_order")
    def test_place_order_slippage_guard_rejection(self, mock_precheck: MagicMock) -> None:
        """Test order placement failure due to SlippageGuard rejection."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value
        self.client.account_key = "test_account_key"

        mock_precheck.return_value = {"SlippageGuardRejection": True, "PreCheckResult": "Rejected"}

        result = self.client.place_order(
            instrument="EURUSD", order_type="Market", side="Buy", amount=1000
        )

        assert result == {
            "OrderRejected": True,
            "Reason": "SlippageGuard: Excessive spread",
        }  # nosec: B101 # pytest assertion
        mock_precheck.assert_called_once()
