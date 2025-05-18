"""
Unit tests for the SaxoClient class.
"""

import os
from unittest.mock import MagicMock, patch

import requests

from src.core.client import SaxoClient


class TestSaxoClient:
    """Test suite for the SaxoClient class."""

    def setup_method(self) -> None:
        """Set up test environment before each test method."""
        os.environ["LIVE_CLIENT_ID"] = "test_client_id"
        os.environ["LIVE_CLIENT_SECRET"] = "test_secret"  # nosec: B105 # Testing value
        os.environ["LIVE_REFRESH_TOKEN"] = "test_token"  # nosec: B105 # Testing value
        os.environ["LIVE_ACCOUNT_KEY"] = "test_account_key"
        
        self.client = SaxoClient(environment="live")

    def teardown_method(self) -> None:
        """Clean up after each test method."""
        for key in ["LIVE_CLIENT_ID", "LIVE_CLIENT_SECRET", "LIVE_REFRESH_TOKEN", 
                  "LIVE_ACCOUNT_KEY"]:
            if key in os.environ:
                del os.environ[key]

    def test_init(self) -> None:
        """Test client initialization."""
        assert self.client.environment == "live"  # nosec: B101 # pytest assertion
        assert self.client.base_url == "https://gateway.saxobank.com/openapi"  # nosec: B101 # pytest assertion
        assert self.client.client_id == "test_client_id"  # nosec: B101 # pytest assertion
        assert self.client.client_secret == "test_secret"  # nosec: B101 # pytest assertion
        assert self.client.refresh_token == "test_token"  # nosec: B101 # pytest assertion
        assert self.client.account_key == "test_account_key"  # nosec: B101 # pytest assertion
        assert self.client.access_token is None  # nosec: B101 # pytest assertion
        assert self.client.token_expiry is None  # nosec: B101 # pytest assertion

    def test_init_sim_environment(self) -> None:
        """Test client initialization with simulation environment."""
        client = SaxoClient(environment="sim")
        assert client.environment == "sim"  # nosec: B101 # pytest assertion
        assert client.base_url == "https://gateway.saxobank.com/sim/openapi"  # nosec: B101 # pytest assertion

    @patch("requests.post")
    def test_authenticate_success(self, mock_post: MagicMock) -> None:
        """Test successful authentication."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test_token"}  # nosec: B105 # Testing value
        mock_post.return_value = mock_response

        result = self.client.authenticate()

        assert result is True  # nosec: B101 # pytest assertion
        assert self.client.access_token == "test_token"  # nosec: B101 # pytest assertion
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://gateway.saxobank.com/openapi/token"  # nosec: B101 # pytest assertion
        assert kwargs["data"]["grant_type"] == "refresh_token"  # nosec: B101 # pytest assertion
        assert kwargs["data"]["refresh_token"] == "test_token"  # nosec: B101 # pytest assertion
        assert kwargs["data"]["client_id"] == "test_client_id"  # nosec: B101 # pytest assertion
        assert kwargs["data"]["client_secret"] == "test_secret"  # nosec: B101 # pytest assertion
        assert kwargs["timeout"] == 30  # nosec: B101 # pytest assertion

    @patch("requests.post")
    def test_authenticate_failure(self, mock_post: MagicMock) -> None:
        """Test authentication failure."""
        mock_post.side_effect = requests.RequestException("Connection error")

        result = self.client.authenticate()

        assert result is False  # nosec: B101 # pytest assertion
        assert self.client.access_token is None  # nosec: B101 # pytest assertion
        
    def test_authenticate_missing_credentials(self) -> None:
        """Test authentication failure due to missing credentials."""
        self.client.client_id = None
        self.client.client_secret = None
        self.client.refresh_token = None
        
        result = self.client.authenticate()
        
        assert result is False  # nosec: B101 # pytest assertion

    @patch("requests.get")
    def test_get_account_info_success(self, mock_get: MagicMock) -> None:
        """Test successful account info retrieval."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"AccountKey": "test_account_key", "Balance": 10000}
        mock_get.return_value = mock_response

        result = self.client.get_account_info()

        assert result == {"AccountKey": "test_account_key", "Balance": 10000}  # nosec: B101 # pytest assertion
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == "https://gateway.saxobank.com/openapi/port/v1/accounts/test_account_key"  # nosec: B101 # pytest assertion
        assert kwargs["headers"]["Authorization"] == "Bearer test_token"  # nosec: B101 # pytest assertion
        assert kwargs["timeout"] == 30  # nosec: B101 # pytest assertion
        
    def test_get_account_info_missing_credentials(self) -> None:
        """Test account info retrieval failure due to missing credentials."""
        self.client.access_token = None
        
        result = self.client.get_account_info()
        
        assert result is None  # nosec: B101 # pytest assertion
    
    @patch("requests.get")
    def test_get_account_info_failure(self, mock_get: MagicMock) -> None:
        """Test account info retrieval failure due to HTTP error."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value
        
        mock_get.side_effect = requests.RequestException("Connection error")
        
        result = self.client.get_account_info()
        
        assert result is None  # nosec: B101 # pytest assertion

    @patch("requests.get")
    def test_get_positions_success(self, mock_get: MagicMock) -> None:
        """Test successful positions retrieval."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Data": [{"PositionId": "123", "Amount": 100}]}
        mock_get.return_value = mock_response

        result = self.client.get_positions()

        assert result == [{"PositionId": "123", "Amount": 100}]  # nosec: B101 # pytest assertion
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == "https://gateway.saxobank.com/openapi/port/v1/positions?FieldGroups=DisplayAndFormat"  # nosec: B101 # pytest assertion
        assert kwargs["headers"]["Authorization"] == "Bearer test_token"  # nosec: B101 # pytest assertion
        assert kwargs["timeout"] == 30  # nosec: B101 # pytest assertion
        
    def test_get_positions_missing_credentials(self) -> None:
        """Test positions retrieval failure due to missing credentials."""
        self.client.access_token = None
        
        result = self.client.get_positions()
        
        assert result is None  # nosec: B101 # pytest assertion
    
    @patch("requests.get")
    def test_get_positions_failure(self, mock_get: MagicMock) -> None:
        """Test positions retrieval failure due to HTTP error."""
        self.client.access_token = "test_token"  # nosec: B105 # Testing value
        
        mock_get.side_effect = requests.RequestException("Connection error")
        
        result = self.client.get_positions()
        
        assert result is None  # nosec: B101 # pytest assertion
