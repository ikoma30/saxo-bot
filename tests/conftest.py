"""
Pytest configuration for Saxo Bot integration tests.
"""

import pytest


@pytest.fixture
def wait_filled(request: pytest.FixtureRequest) -> int:
    """Return the wait-filled parameter value."""
    wait_time: int = int(request.config.getoption("--wait-filled"))
    return wait_time
