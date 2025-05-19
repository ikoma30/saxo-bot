#!/usr/bin/env python3
"""
Generate all required artifacts for PR #10.

This script runs all the necessary scripts to generate:
1. SIM canary reports
2. Prometheus metrics snapshot
3. Evidence of executed trades
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("artifacts")

SCRIPTS_DIR = Path(__file__).parent
REPORTS_DIR = SCRIPTS_DIR.parent / "reports"


def run_script(script_path: str, args: list[str] | None = None) -> bool:
    """
    Run a Python script as a subprocess.
    
    Args:
        script_path: Path to the script to run
        args: Additional arguments to pass to the script
    
    Returns:
        bool: True if the script ran successfully, False otherwise
    """
    if args is None:
        args = []
    
    cmd = [sys.executable, script_path] + args
    logger.info(f"Running script: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        logger.info(f"Script {script_path} ran successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Script {script_path} failed with error: {e.returncode}")
        logger.error(f"Stderr: {e.stderr}")
        return False


def main() -> int:
    """
    Generate all required artifacts.
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    main_bot_result = run_script(str(SCRIPTS_DIR / "modified_run_canary_test.py"))
    micro_rev_bot_result = run_script(
        str(SCRIPTS_DIR / "modified_run_canary_test.py"), 
        ["EURJPY", "10", "0.01", "Micro-Rev"]
    )
    
    prometheus_result = run_script(str(SCRIPTS_DIR / "get_prometheus_metrics.py"))
    
    screenshot_result = run_script(str(SCRIPTS_DIR / "capture_saxo_trader_go_selenium.py"))
    
    success = all([
        main_bot_result,
        micro_rev_bot_result,
        prometheus_result,
        screenshot_result,
    ])
    
    if success:
        logger.info("All artifacts generated successfully")
        logger.info(f"Artifacts can be found in {REPORTS_DIR}")
        return 0
    else:
        logger.error("Failed to generate all artifacts")
        return 1


if __name__ == "__main__":
    sys.exit(main())
