"""
Integration tests for token validity.

Tests SIM Refresh-Token 24h validity check.
"""

import datetime
import logging
import os
import time

import pytest

from src.core.saxo_client import SaxoClient
from tests.utils.skip_helpers import skip_if_no_sim_token

logger = logging.getLogger("test")


@pytest.mark.integration
def test_sim_token_exchange() -> None:
    """Test that SIM refresh token can be exchanged for an access token."""
    skip_if_no_sim_token()

    client = SaxoClient(environment="sim")
    result = client.authenticate()

    assert result  # nosec: B101 # pytest assertion
    assert client.access_token is not None  # nosec: B101 # pytest assertion


@pytest.mark.integration
def test_sim_token_24h_validity() -> None:
    """
    Test that SIM refresh token has at least 24h validity remaining.

    This test verifies that the refresh token has at least 24 hours of
    validity remaining, which is required for operational resilience.
    """
    skip_if_no_sim_token()

    start_time = time.time()

    client = SaxoClient(environment="sim")
    result = client.authenticate()

    assert result  # nosec: B101 # pytest assertion
    assert client.access_token is not None  # nosec: B101 # pytest assertion

    token_expiry = client.token_expiry

    time.sleep(5)

    client.access_token = None
    result = client.authenticate()

    assert result  # nosec: B101 # pytest assertion
    assert client.access_token is not None  # nosec: B101 # pytest assertion

    if token_expiry:
        expiry_time = datetime.datetime.fromisoformat(
            token_expiry.replace("Z", "+00:00")
        ).timestamp()
        remaining_validity_hours = (expiry_time - start_time) / 3600

        logger.info(f"Token validity remaining: {remaining_validity_hours:.2f} hours")

        assert remaining_validity_hours >= 24  # nosec: B101 # pytest assertion
    else:
        pytest.fail("Token expiry time not available")
