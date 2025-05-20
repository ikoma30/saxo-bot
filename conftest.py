"""
Pytest configuration file.

This file configures pytest to be able to import modules from the src directory.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom command line options to pytest."""
    parser.addoption(
        "--wait-filled",
        action="store",
        default="0",
        help="Wait for orders to be filled for N seconds",
    )


@pytest.fixture
def wait_filled(request: pytest.FixtureRequest) -> int:
    """Return the wait-filled option value."""
    return int(request.config.getoption("--wait-filled"))
