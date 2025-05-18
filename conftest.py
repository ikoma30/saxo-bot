"""
Pytest configuration file.

This file configures pytest to be able to import modules from the src directory.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
