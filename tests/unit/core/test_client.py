"""
Unit tests for the SaxoClient class.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

import pytest
import requests

from src.core.client import SaxoClient


class TestSaxoClient:
    """Test suite for the SaxoClient class."""

    def setup_method(self):
        """Set up test environment before each test method."""
        os.environ["LIVE_CLIENT_ID"] = "test_client_id"
        os.environ["LIVE_CLIENT_SECRET"] = "test_client_secret"
        os.environ["LIVE_REFRESH_TOKEN"] = "test_refresh_token"
        os.environ["LIVE_ACCOUNT_KEY"] = "test_account_key"
        
        self.client = SaxoClient(environment="live")

    def teardown_method(self):
        """Clean up after each test method."""
        for key in ["LIVE_CLIENT_ID", "LIVE_CLIENT_SECRET", "LIVE_REFRESH_TOKEN", "LIVE_ACCOUNT_KEY"]:
            if key in os.environ:
                del os.environ[key]

    def test_init(self):
        """Test client initialization."""
        assert self.client.environment == "live"
        assert self.client.base_url == "https://gateway.saxobank.com/openapi"
        assert self.client.client_id == "test_client_id"
        assert self.client.client_secret == "test_client_secret"
        assert self.client.refresh_token == "test_refresh_token"
        assert self.client.account_key == "test_account_key"
        assert self.client.access_token is None
        assert self.client.token_expiry is None

    def test_init_sim_environment(self):
        """Test client initialization with simulation environment."""
        client = SaxoClient(environment="sim")
        assert client.environment == "sim"
        assert client.base_url == "https://gateway.saxobank.com/sim/openapi"

    @patch("requests.post")
    def test_authenticate_success(self, mock_post):
        """Test successful authentication."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test_access_token"}
        mock_post.return_value = mock_response

        result = self.client.authenticate()

        assert result is True
        assert self.client.access_token == "test_access_token"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://gateway.saxobank.com/openapi/token"
        assert kwargs["data"]["grant_type"] == "refresh_token"
        assert kwargs["data"]["refresh_token"] == "test_refresh_token"
        assert kwargs["data"]["client_id"] == "test_client_id"
        assert kwargs["data"]["client_secret"] == "test_client_secret"
        assert kwargs["timeout"] == 30

    @patch("requests.post")
    def test_authenticate_failure(self, mock_post):
        """Test authentication failure."""
        mock_post.side_effect = requests.RequestException("Connection error")

        result = self.client.authenticate()

        assert result is False
        assert self.client.access_token is None

    @patch("requests.get")
    def test_get_account_info_success(self, mock_get):
        """Test successful account info retrieval."""
        self.client.access_token = "test_access_token"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"AccountKey": "test_account_key", "Balance": 10000}
        mock_get.return_value = mock_response

        result = self.client.get_account_info()

        assert result == {"AccountKey": "test_account_key", "Balance": 10000}
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == "https://gateway.saxobank.com/openapi/port/v1/accounts/test_account_key"
        assert kwargs["headers"]["Authorization"] == "Bearer test_access_token"
        assert kwargs["timeout"] == 30

    @patch("requests.get")
    def test_get_positions_success(self, mock_get):
        """Test successful positions retrieval."""
        self.client.access_token = "test_access_token"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Data": [{"PositionId": "123", "Amount": 100}]}
        mock_get.return_value = mock_response

        result = self.client.get_positions()

        assert result == [{"PositionId": "123", "Amount": 100}]
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == "https://gateway.saxobank.com/openapi/port/v1/positions?FieldGroups=DisplayAndFormat"
        assert kwargs["headers"]["Authorization"] == "Bearer test_access_token"
        assert kwargs["timeout"] == 30
