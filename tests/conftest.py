"""
Pytest configuration for Saxo Bot integration tests.
"""

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom command line options for pytest."""
    parser.addoption(
        "--wait-filled",
        type=int,
        default=60,
        help="Maximum time to wait for orders to be filled (in seconds)",
    )


@pytest.fixture
def wait_filled_seconds(request: pytest.FixtureRequest) -> int:
    """Return the wait-filled parameter value."""
    wait_time: int = request.config.getoption("--wait-filled")
    return wait_time
