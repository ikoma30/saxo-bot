"""
Pytest configuration for Saxo Bot integration tests.
"""

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom command line options for pytest."""
    parser.addoption(
        "--wait-filled",
        action="store",
        default="60",
        help="Wait for orders to be filled for N seconds",
    )


@pytest.fixture
def wait_filled(request: pytest.FixtureRequest) -> int:
    """Return the wait-filled parameter value."""
    wait_time: int = int(request.config.getoption("--wait-filled"))
    return wait_time
