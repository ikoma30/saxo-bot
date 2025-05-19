"""
Tests for the UIC mapping utility.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.utils.uic_map import UICMap


class TestUICMap:
    """Tests for the UICMap class."""

    def test_init(self) -> None:
        """Test initialization."""
        client = MagicMock()
        uic_map = UICMap(client)
        
        assert uic_map._client == client
        assert uic_map._uic_cache == {}
        assert uic_map._symbol_cache == {}

    def test_get_uic_from_cache(self) -> None:
        """Test getting UIC from cache."""
        uic_map = UICMap()
        uic_map._uic_cache = {"USDJPY": 21}
        
        result = uic_map.get_uic("USDJPY")
        
        assert result == 21

    @patch("requests.get")
    def test_get_uic_from_api(self, mock_get: MagicMock) -> None:
        """Test getting UIC from API."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "Data": [
                {"Symbol": "USDJPY", "Identifier": 21}
            ]
        }
        mock_get.return_value = mock_response
        mock_response.raise_for_status.return_value = None
        
        client = MagicMock()
        client.access_token = "mock-token"
        client.base_url = "https://mock-url"
        
        uic_map = UICMap(client)
        result = uic_map.get_uic("USDJPY")
        
        assert result == 21
        assert uic_map._uic_cache == {"USDJPY": 21}
        assert uic_map._symbol_cache == {21: "USDJPY"}

    def test_get_symbol_from_cache(self) -> None:
        """Test getting symbol from cache."""
        uic_map = UICMap()
        uic_map._symbol_cache = {21: "USDJPY"}
        
        result = uic_map.get_symbol(21)
        
        assert result == "USDJPY"

    @patch("requests.get")
    def test_get_symbol_from_api(self, mock_get: MagicMock) -> None:
        """Test getting symbol from API."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "Symbol": "USDJPY",
            "Identifier": 21
        }
        mock_get.return_value = mock_response
        mock_response.raise_for_status.return_value = None
        
        client = MagicMock()
        client.access_token = "mock-token"
        client.base_url = "https://mock-url"
        
        uic_map = UICMap(client)
        result = uic_map.get_symbol(21)
        
        assert result == "USDJPY"
        assert uic_map._symbol_cache == {21: "USDJPY"}
        assert uic_map._uic_cache == {"USDJPY": 21}

    @patch("requests.get")
    def test_get_uic_api_error(self, mock_get: MagicMock) -> None:
        """Test error handling when API call fails."""
        mock_get.side_effect = Exception("API error")
        
        client = MagicMock()
        client.access_token = "mock-token"
        client.base_url = "https://mock-url"
        
        uic_map = UICMap(client)
        result = uic_map.get_uic("USDJPY")
        
        assert result is None
        assert uic_map._uic_cache == {}
        assert uic_map._symbol_cache == {}
