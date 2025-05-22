"""
Skip helpers for tests.

This module provides helper functions for skipping tests under certain conditions.
"""

import os
import pytest


def skip_if_no_sim_token() -> None:
    """
    Skip test if SIM_REFRESH_TOKEN is not set.

    This helper is used to skip tests that require a SIM_REFRESH_TOKEN
    when running locally, while still allowing them to run in CI.
    """
    if not os.getenv("SIM_REFRESH_TOKEN"):
        pytest.skip("SIM_REFRESH_TOKEN not set – skipping live canary")
