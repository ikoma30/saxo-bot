"""
Pytest configuration for integration tests.
"""

import pytest


def pytest_addoption(parser):
    """Add custom command-line options for integration tests."""
    parser.addoption(
        "--wait-filled",
        action="store",
        default="0",
        help="Wait for order to be filled/executed for specified seconds",
    )
