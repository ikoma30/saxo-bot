#!/usr/bin/env python3
"""
Capture a screenshot from SaxoTraderGO for trade evidence.

This script uses Selenium to automate browser interaction with SaxoTraderGO,
logs in, navigates to the account page, and captures a screenshot of executed trades.
"""

import datetime
import logging
import os
import sys
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("saxo_trader_go")

REPORTS_DIR = Path(__file__).parent.parent / "reports"
ACCOUNT_KEY = "PjXXja494N5ZimF-lPRqgQ=="
ACCOUNT_ID = "TRIAL_20477947"


def capture_screenshot() -> str:
    """
    Capture a screenshot from SaxoTraderGO showing executed trades.

    Returns:
        str: Path to the saved screenshot file
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_file = REPORTS_DIR / f"saxo_trader_go_{timestamp}.png"

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        logger.info("Navigating to SaxoTraderGO")
        driver.get("https://www.saxotrader.com/sim/login/")

        WebDriverWait(driver, 10).until(
            expected_conditions.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
        )

        username = os.environ.get("SIM_USERNAME")
        password = os.environ.get("SIM_PASSWORD")

        if not username or not password:
            logger.error("SIM_USERNAME or SIM_PASSWORD environment variables not set")
            return ""

        logger.info("Logging in to SaxoTraderGO")
        driver.find_element(By.CSS_SELECTOR, "input[type='text']").send_keys(username)
        driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        WebDriverWait(driver, 30).until(
            expected_conditions.presence_of_element_located((By.CSS_SELECTOR, ".dashboard"))
        )

        logger.info(f"Navigating to account {ACCOUNT_ID}")
        driver.find_element(By.CSS_SELECTOR, "a[href*='accounts']").click()

        WebDriverWait(driver, 10).until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, f"div[data-account-id='{ACCOUNT_ID}']")
            )
        )
        driver.find_element(By.CSS_SELECTOR, f"div[data-account-id='{ACCOUNT_ID}']").click()

        logger.info("Navigating to trade history")
        driver.find_element(By.CSS_SELECTOR, "a[href*='history']").click()

        WebDriverWait(driver, 10).until(
            expected_conditions.presence_of_element_located((By.CSS_SELECTOR, ".trade-history"))
        )

        logger.info(f"Capturing screenshot to {screenshot_file}")
        driver.save_screenshot(str(screenshot_file))

        logger.info(f"Screenshot saved to {screenshot_file}")
        return str(screenshot_file)
    except Exception as e:
        logger.error(f"Failed to capture screenshot: {str(e)}")
        return ""
    finally:
        driver.quit()


def main() -> int:
    """
    Capture a screenshot from SaxoTraderGO.

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    try:
        screenshot_file = capture_screenshot()
        if not screenshot_file:
            logger.error("Failed to capture screenshot")
            return 1

        logger.info(f"Successfully captured screenshot: {screenshot_file}")
        return 0
    except Exception as e:
        logger.error(f"Failed to capture screenshot: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
