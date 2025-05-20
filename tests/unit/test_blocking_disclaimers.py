"""
Unit tests for the BlockingDisclaimers handling in SaxoClient.
"""

import os
from unittest.mock import MagicMock, patch

from src.common.exceptions import SaxoApiError
from src.core.saxo_client import SaxoClient


class TestBlockingDisclaimers:
    """Test suite for the BlockingDisclaimers handling in SaxoClient."""

    def setup_method(self) -> None:
        """Set up test environment before each test method."""
        os.environ["LIVE_CLIENT_ID"] = "test_client_id"
        os.environ["LIVE_CLIENT_SECRET"] = "test_secret"  # nosec: B105 # Testing value
        os.environ["LIVE_REFRESH_TOKEN"] = "test_token"  # nosec: B105 # Testing value
        os.environ["LIVE_ACCOUNT_KEY"] = "test_account_key"
        os.environ["USE_TRADE_V3"] = "false"

        self.client = SaxoClient(environment="live")
        self.client.access_token = "test_token"  # nosec: B105 # Testing value
        self.client.account_key = "test_account_key"

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

    @patch("src.core.saxo_client.request")
    @patch("src.core.saxo_client.SaxoClient._precheck_order")
    @patch("src.core.saxo_client.SaxoClient._accept_disclaimer")
    def test_place_order_with_disclaimers(
        self, mock_accept: MagicMock, mock_precheck: MagicMock, mock_request: MagicMock
    ) -> None:
        """Test order placement with disclaimers: precheck → disclaimers → accept → precheck OK → order sent."""
        mock_precheck.side_effect = [
            {"BlockingDisclaimers": [{"Id": "disclaimer1"}, {"Id": "disclaimer2"}]},
            {"PreCheckResult": "OK"},  # Second precheck is successful
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
        assert mock_accept.call_count == 2  # nosec: B101 # pytest assertion
        mock_accept.assert_any_call("disclaimer1")
        mock_accept.assert_any_call("disclaimer2")
        mock_request.assert_called_once()

    @patch("src.core.saxo_client.request")
    @patch("src.core.saxo_client.SaxoClient._precheck_order")
    def test_place_order_without_disclaimers(
        self, mock_precheck: MagicMock, mock_request: MagicMock
    ) -> None:
        """Test order placement without disclaimers: precheck OK first time → order sent directly."""
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

    @patch("src.core.saxo_client.SaxoClient._precheck_order")
    @patch("src.core.saxo_client.SaxoClient._accept_disclaimer")
    def test_place_order_disclaimer_acceptance_failure(
        self, mock_accept: MagicMock, mock_precheck: MagicMock
    ) -> None:
        """Test order placement failure due to disclaimer acceptance failure."""
        mock_precheck.return_value = {"BlockingDisclaimers": [{"Id": "disclaimer1"}]}

        mock_accept.return_value = False

        result = self.client.place_order(
            instrument="EURUSD", order_type="Market", side="Buy", amount=1000
        )

        assert result is None  # nosec: B101 # pytest assertion
        mock_precheck.assert_called_once()
        mock_accept.assert_called_once_with("disclaimer1")

    @patch("src.core.saxo_client.SaxoClient._precheck_order")
    @patch("src.core.saxo_client.SaxoClient._accept_disclaimer")
    @patch("src.core.saxo_client.request")
    def test_place_order_persistent_disclaimers(
        self, mock_request: MagicMock, mock_accept: MagicMock, mock_precheck: MagicMock
    ) -> None:
        """Test order placement failure due to persistent disclaimers after acceptance."""
        mock_precheck.side_effect = [
            {"BlockingDisclaimers": [{"Id": "disclaimer1"}]},
            {"BlockingDisclaimers": [{"Id": "disclaimer1"}]},  # Disclaimers still present
        ]

        mock_accept.return_value = True

        result = self.client.place_order(
            instrument="EURUSD", order_type="Market", side="Buy", amount=1000
        )

        assert result is None  # nosec: B101 # pytest assertion
        assert mock_precheck.call_count == 2  # nosec: B101 # pytest assertion
        mock_accept.assert_called_once_with("disclaimer1")
        mock_request.assert_not_called()

    @patch("src.core.saxo_client.SaxoClient._precheck_order")
    @patch("src.core.saxo_client.SaxoClient._accept_disclaimer")
    @patch("src.core.saxo_client.request")
    def test_place_order_retry_on_transient_error(
        self, mock_request: MagicMock, mock_accept: MagicMock, mock_precheck: MagicMock
    ) -> None:
        """Test retry logic for transient errors (5xx/429) on disclaimer acceptance."""
        mock_precheck.side_effect = [
            {"BlockingDisclaimers": [{"Id": "disclaimer1"}]},
            {"PreCheckResult": "OK"},  # Second precheck is successful
        ]

        mock_accept.side_effect = [
            SaxoApiError("Service Unavailable", 503, {"Message": "Service Unavailable"}),
            True,
        ]

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"OrderId": "123456"}
        mock_request.return_value = mock_response

        with patch("time.sleep"):
            result = self.client.place_order(
                instrument="EURUSD", order_type="Market", side="Buy", amount=1000
            )

        assert result == {"OrderId": "123456"}  # nosec: B101 # pytest assertion
        assert mock_precheck.call_count == 2  # nosec: B101 # pytest assertion
        assert mock_accept.call_count == 2  # nosec: B101 # pytest assertion
        mock_request.assert_called_once()

    @patch("src.core.saxo_client.SaxoClient._handle_blocking_disclaimers")
    @patch("src.core.saxo_client.SaxoClient._precheck_order")
    @patch("src.core.saxo_client.request")
    def test_place_order_with_handle_blocking_disclaimers(
        self, mock_request: MagicMock, mock_precheck: MagicMock, mock_handle: MagicMock
    ) -> None:
        """Test that place_order uses _handle_blocking_disclaimers method."""
        precheck_result = {"BlockingDisclaimers": [{"Id": "disclaimer1"}]}
        mock_precheck.return_value = precheck_result

        mock_handle.return_value = {"PreCheckResult": "OK"}

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"OrderId": "123456"}
        mock_request.return_value = mock_response

        result = self.client.place_order(
            instrument="EURUSD", order_type="Market", side="Buy", amount=1000
        )

        assert result == {"OrderId": "123456"}  # nosec: B101 # pytest assertion
        mock_precheck.assert_called_once()
        mock_handle.assert_called_once_with(precheck_result)
        mock_request.assert_called_once()

    @patch("src.core.saxo_client.SaxoClient._accept_disclaimer")
    def test_handle_blocking_disclaimers(self, mock_accept: MagicMock) -> None:
        """Test _handle_blocking_disclaimers method directly."""
        mock_accept.return_value = True

        precheck_resp = {"BlockingDisclaimers": [{"Id": "disclaimer1"}, {"Id": "disclaimer2"}]}

        result = self.client._handle_blocking_disclaimers(precheck_resp)

        assert result is None  # nosec: B101 # pytest assertion
        assert mock_accept.call_count == 2  # nosec: B101 # pytest assertion
        mock_accept.assert_any_call("disclaimer1")
        mock_accept.assert_any_call("disclaimer2")

    def test_handle_blocking_disclaimers_no_disclaimers(self) -> None:
        """Test _handle_blocking_disclaimers method with no disclaimers."""
        precheck_resp = {"PreCheckResult": "OK"}

        result = self.client._handle_blocking_disclaimers(precheck_resp)

        assert result == precheck_resp  # nosec: B101 # pytest assertion

    @patch("src.core.saxo_client.SaxoClient._accept_disclaimer")
    def test_handle_blocking_disclaimers_missing_id(self, mock_accept: MagicMock) -> None:
        """Test _handle_blocking_disclaimers method with a disclaimer missing an Id."""
        precheck_resp = {"BlockingDisclaimers": [{"Id": "disclaimer1"}, {"NoId": "missing"}]}

        result = self.client._handle_blocking_disclaimers(precheck_resp)

        assert result is None  # nosec: B101 # pytest assertion
        mock_accept.assert_called_once_with("disclaimer1")

    @patch("src.core.saxo_client.SaxoClient._accept_disclaimer")
    def test_handle_blocking_disclaimers_acceptance_failure(self, mock_accept: MagicMock) -> None:
        """Test _handle_blocking_disclaimers method with disclaimer acceptance failure."""
        mock_accept.return_value = False

        precheck_resp = {"BlockingDisclaimers": [{"Id": "disclaimer1"}]}

        result = self.client._handle_blocking_disclaimers(precheck_resp)

        assert result is None  # nosec: B101 # pytest assertion
        mock_accept.assert_called_once_with("disclaimer1")
