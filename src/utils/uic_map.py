"""
UIC Mapping Utility Module

Maps symbol names to numeric UICs via the /ref/v1/instruments/details endpoint.
"""

import logging
import os
from typing import Dict, Optional, Any

import requests

logger = logging.getLogger("uic_map")

class UICMap:
    """Utility for mapping between symbol names and numeric UICs."""

    def __init__(self, client=None) -> None:
        """
        Initialize the UIC Map.

        Args:
            client: Optional SaxoClient instance for API access
        """
        self._client = client
        self._uic_cache: Dict[str, int] = {}
        self._symbol_cache: Dict[int, str] = {}
        self.timeout = 5  # 5 second timeout

    def get_uic(self, symbol: str) -> Optional[int]:
        """
        Get the UIC for a symbol.

        Args:
            symbol: The symbol to lookup (e.g., "USDJPY")

        Returns:
            The UIC as an integer, or None if not found
        """
        if symbol in self._uic_cache:
            return self._uic_cache[symbol]

        if self._client and hasattr(self._client, "access_token"):
            uic = self._fetch_uic_from_api(symbol)
            if uic:
                self._uic_cache[symbol] = uic
                self._symbol_cache[uic] = symbol
                return uic

        logger.warning(f"UIC not found for symbol: {symbol}")
        return None

    def get_symbol(self, uic: int) -> Optional[str]:
        """
        Get the symbol for a UIC.

        Args:
            uic: The UIC to lookup

        Returns:
            The symbol as a string, or None if not found
        """
        if uic in self._symbol_cache:
            return self._symbol_cache[uic]

        if self._client and hasattr(self._client, "access_token"):
            symbol = self._fetch_symbol_from_api(uic)
            if symbol:
                self._symbol_cache[uic] = symbol
                self._uic_cache[symbol] = uic
                return symbol

        logger.warning(f"Symbol not found for UIC: {uic}")
        return None

    def _fetch_uic_from_api(self, symbol: str) -> Optional[int]:
        """
        Fetch a UIC from the Saxo API.

        Args:
            symbol: The symbol to lookup

        Returns:
            The UIC as an integer, or None if not found
        """
        if not self._client or not hasattr(self._client, "access_token"):
            logger.error("Client not initialized or authenticated")
            return None

        headers = {"Authorization": f"Bearer {self._client.access_token}"}
        base_url = self._client.base_url
        endpoint = "/ref/v1/instruments/details"
        params = {
            "AssetTypes": "FxSpot",
            "Keywords": symbol,
            "IncludeNonTradable": "false",
        }

        try:
            logger.info(f"Fetching UIC for symbol {symbol}")
            response = requests.get(
                f"{base_url}{endpoint}",
                headers=headers,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data: Dict[str, Any] = response.json()

            if "Data" in data and data["Data"]:
                for instrument in data["Data"]:
                    if instrument.get("Symbol") == symbol:
                        uic = instrument.get("Identifier")
                        if uic:
                            logger.info(f"Found UIC {uic} for symbol {symbol}")
                            return int(uic)

            logger.warning(f"No matching instrument found for {symbol}")
            return None
        except requests.HTTPError as e:
            logger.error(f"Failed to fetch UIC for {symbol}: {str(e)}")
            return None
        except requests.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return None

    def _fetch_symbol_from_api(self, uic: int) -> Optional[str]:
        """
        Fetch a symbol from the Saxo API.

        Args:
            uic: The UIC to lookup

        Returns:
            The symbol as a string, or None if not found
        """
        if not self._client or not hasattr(self._client, "access_token"):
            logger.error("Client not initialized or authenticated")
            return None

        headers = {"Authorization": f"Bearer {self._client.access_token}"}
        base_url = self._client.base_url
        endpoint = f"/ref/v1/instruments/details/{uic}"

        try:
            logger.info(f"Fetching symbol for UIC {uic}")
            response = requests.get(
                f"{base_url}{endpoint}",
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data: Dict[str, Any] = response.json()

            if "Symbol" in data:
                symbol = data["Symbol"]
                logger.info(f"Found symbol {symbol} for UIC {uic}")
                return symbol

            logger.warning(f"No matching instrument found for UIC {uic}")
            return None
        except requests.HTTPError as e:
            logger.error(f"Failed to fetch symbol for UIC {uic}: {str(e)}")
            return None
        except requests.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return None
