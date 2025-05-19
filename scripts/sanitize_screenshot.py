#!/usr/bin/env python3
"""
Sanitize screenshots from SaxoTraderGO for security and privacy.

This script takes a screenshot and sanitizes it by adding black boxes over sensitive information
such as account IDs, account keys, and other personally identifiable information.
"""

import argparse
import logging
import os
import sys
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("sanitize_screenshot")

REDACT_REGIONS = [
    (100, 150, 300, 180),
    (100, 200, 300, 230),
    (100, 250, 300, 280),
    (100, 300, 300, 330),
]


def sanitize_screenshot(
    input_file: str, output_file: str, regions: Optional[List[Tuple[int, int, int, int]]] = None
) -> bool:
    """
    Sanitize a screenshot by adding black boxes over sensitive information.

    Args:
        input_file: Path to the input screenshot file
        output_file: Path to the output sanitized screenshot file
        regions: List of regions to redact (x1, y1, x2, y2)

    Returns:
        bool: True if sanitization was successful, False otherwise
    """
    try:
        logger.info(f"Sanitizing screenshot: {input_file}")

        if not os.path.exists(input_file):
            logger.error(f"Input file does not exist: {input_file}")
            return False

        if regions is None:
            regions = REDACT_REGIONS

        img = Image.open(input_file)
        draw = ImageDraw.Draw(img)

        for region in regions:
            draw.rectangle(region, fill="black")

        try:
            font = ImageFont.truetype("Arial", 20)
        except IOError:
            font = ImageFont.load_default()

        draw.rectangle((0, 0, img.width, 40), fill="#ffeeee")
        draw.text(
            (10, 10),
            "Notice: This screenshot has been sanitized for security and privacy reasons.",
            fill="black",
            font=font,
        )

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        img.save(output_file)

        logger.info(f"Sanitized screenshot saved to: {output_file}")
        return True

    except Exception as e:
        logger.error(f"Error sanitizing screenshot: {str(e)}")
        return False


def main() -> int:
    """
    Parse command line arguments and sanitize screenshot.

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(description="Sanitize screenshot")
    parser.add_argument("--input", required=True, help="Path to input screenshot file")
    parser.add_argument("--output", required=True, help="Path to output sanitized screenshot file")

    args = parser.parse_args()

    if sanitize_screenshot(args.input, args.output):
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
