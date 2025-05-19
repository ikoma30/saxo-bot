#!/usr/bin/env python3
"""
Capture a screenshot from SaxoTraderGO for trade evidence.

This script uses Playwright to automate browser interaction with SaxoTraderGO,
logs in, navigates to the account page, and captures a screenshot of executed trades.
"""

import datetime
import logging
import os
import sys
from pathlib import Path

import asyncio
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("saxo_trader_go")

REPORTS_DIR = Path(__file__).parent.parent / "reports"
ACCOUNT_KEY = "PjXXja494N5ZimF-lPRqgQ=="
ACCOUNT_ID = "TRIAL_20477947"


async def capture_screenshot() -> str:
    """
    Capture a screenshot from SaxoTraderGO showing executed trades.

    Returns:
        str: Path to the saved screenshot file
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_file = REPORTS_DIR / f"saxo_trader_go_{timestamp}.png"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        logger.info("Navigating to SaxoTraderGO")
        await page.goto("https://www.saxotrader.com/sim/login/")
        
        await page.wait_for_selector("input[type='text']")
        
        username = os.environ.get("SIM_USERNAME")
        password = os.environ.get("SIM_PASSWORD")
        
        if not username or not password:
            logger.error("SIM_USERNAME or SIM_PASSWORD environment variables not set")
            await browser.close()
            return ""
        
        logger.info("Logging in to SaxoTraderGO")
        await page.fill("input[type='text']", username)
        await page.fill("input[type='password']", password)
        await page.click("button[type='submit']")
        
        await page.wait_for_selector(".dashboard")
        
        logger.info(f"Navigating to account {ACCOUNT_ID}")
        await page.click("a[href*='accounts']")
        
        await page.wait_for_selector(f"div[data-account-id='{ACCOUNT_ID}']")
        await page.click(f"div[data-account-id='{ACCOUNT_ID}']")
        
        logger.info("Navigating to trade history")
        await page.click("a[href*='history']")
        
        await page.wait_for_selector(".trade-history")
        
        logger.info(f"Capturing screenshot to {screenshot_file}")
        await page.screenshot(path=str(screenshot_file))
        
        await browser.close()
    
    logger.info(f"Screenshot saved to {screenshot_file}")
    return str(screenshot_file)


def main() -> int:
    """
    Capture a screenshot from SaxoTraderGO.
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    try:
        screenshot_file = asyncio.run(capture_screenshot())
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
