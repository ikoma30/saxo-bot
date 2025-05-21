from unittest.mock import MagicMock
from src.core.saxo_client import SaxoClient


class TestSaxoClientUnknownStatus:
    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.client = SaxoClient(environment="live")

    def test_update_trade_metrics_unknown_status(self) -> None:
        """Test updating trade metrics when an order has an unknown status."""
        self.client.last_trade_status = MagicMock()

        self.client._update_trade_metrics({"Status": "SomeUnknownStatus"})

        assert (
            self.client.last_trade_status.labels.call_count >= 1
        )  # nosec: B101 # pytest assertion
        self.client.last_trade_status.labels.assert_any_call(
            env=self.client.environment, status="SomeUnknownStatus"
        )
