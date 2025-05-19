"""
Units Converter Utility Module

Converts lot sizes to appropriate units for different asset types.
"""

import logging
from decimal import Decimal
from typing import Union, Dict, Optional

logger = logging.getLogger("units_converter")

LOT_TO_UNITS_FACTOR: Dict[str, int] = {
    "FxSpot": 100000,  # 1 lot = 100,000 units for major pairs
    "FxMetals": 100,  # 1 lot = 100 oz for metals
    "CFD": 1,  # Varies by instrument, default 1:1
}

INSTRUMENT_SPECIFIC_FACTORS: Dict[str, int] = {
    "XAUUSD": 100,  # Gold
    "XAGUSD": 5000,  # Silver
}


def lot_to_units(
    amount: Union[Decimal, float, int], asset_type: str = "FxSpot", instrument: Optional[str] = None
) -> int:
    """
    Convert lot amount to appropriate units.

    Args:
        amount: Amount in lots
        asset_type: The type of asset (FxSpot, FxMetals, CFD)
        instrument: The specific instrument symbol (optional)

    Returns:
        Amount in units
    """
    if isinstance(amount, Decimal):
        decimal_amount = amount
    else:
        decimal_amount = Decimal(str(amount))

    if instrument and instrument in INSTRUMENT_SPECIFIC_FACTORS:
        factor = INSTRUMENT_SPECIFIC_FACTORS[instrument]
        logger.debug(f"Using instrument-specific factor {factor} for {instrument}")
    elif asset_type in LOT_TO_UNITS_FACTOR:
        factor = LOT_TO_UNITS_FACTOR[asset_type]
        logger.debug(f"Using asset type factor {factor} for {asset_type}")
    else:
        factor = LOT_TO_UNITS_FACTOR["FxSpot"]
        logger.warning(f"Unknown asset type {asset_type}, using default factor {factor}")

    units = int(decimal_amount * Decimal(factor))
    logger.debug(f"Converted {amount} lots to {units} units for {asset_type}/{instrument}")
    return units
