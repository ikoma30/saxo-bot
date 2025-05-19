"""
Tests for the units converter utility.
"""

import pytest
from decimal import Decimal

from src.utils.units_converter import lot_to_units


class TestUnitsConverter:
    """Tests for the units converter functions."""

    def test_lot_to_units_fx_spot(self) -> None:
        """Test converting lots to units for FX Spot."""
        result = lot_to_units(Decimal("0.01"), "FxSpot")
        assert result == 1000
        
        result = lot_to_units(0.01, "FxSpot")
        assert result == 1000
        
        result = lot_to_units(1, "FxSpot")
        assert result == 100000

    def test_lot_to_units_fx_metals(self) -> None:
        """Test converting lots to units for FX Metals."""
        result = lot_to_units(Decimal("0.01"), "FxMetals")
        assert result == 1
        
        result = lot_to_units(1, "FxMetals")
        assert result == 100

    def test_lot_to_units_cfd(self) -> None:
        """Test converting lots to units for CFD."""
        result = lot_to_units(Decimal("0.01"), "CFD")
        assert result == 0
        
        result = lot_to_units(1, "CFD")
        assert result == 1

    def test_lot_to_units_instrument_specific(self) -> None:
        """Test converting lots to units for specific instruments."""
        result = lot_to_units(Decimal("0.01"), "FxMetals", "XAUUSD")
        assert result == 1
        
        result = lot_to_units(Decimal("0.01"), "FxMetals", "XAGUSD")
        assert result == 50

    def test_lot_to_units_unknown_asset_type(self) -> None:
        """Test converting lots to units for unknown asset type."""
        result = lot_to_units(Decimal("0.01"), "Unknown")
        assert result == 1000  # Default to FxSpot
