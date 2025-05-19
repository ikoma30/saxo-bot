#!/usr/bin/env python3
"""
Sanitize HTML trade report for security and privacy.

This script takes an HTML trade report and sanitizes it by removing sensitive information
and formatting it for inclusion in PR artifacts.
"""

import argparse
import logging
import os
import re
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("sanitize_html")


def sanitize_html(input_file: str, output_file: str) -> bool:
    """
    Sanitize an HTML trade report by removing sensitive information.

    Args:
        input_file: Path to the input HTML file
        output_file: Path to the output sanitized HTML file

    Returns:
        bool: True if sanitization was successful, False otherwise
    """
    try:
        logger.info(f"Sanitizing HTML file: {input_file}")
        
        if not os.path.exists(input_file):
            logger.error(f"Input file does not exist: {input_file}")
            return False
            
        with open(input_file, "r") as f:
            html_content = f.read()
            
        sanitized_content = re.sub(r'(Account\s*ID:?\s*)[A-Za-z0-9_-]+', r'\1REDACTED', html_content)
        sanitized_content = re.sub(r'(Account\s*Key:?\s*)[A-Za-z0-9_-]+', r'\1REDACTED', sanitized_content)
        sanitized_content = re.sub(r'(Client\s*ID:?\s*)[A-Za-z0-9_-]+', r'\1REDACTED', sanitized_content)
        sanitized_content = re.sub(r'(User\s*ID:?\s*)[A-Za-z0-9_-]+', r'\1REDACTED', sanitized_content)
        
        sanitized_content = sanitized_content.replace(
            '<body>',
            '<body>\n<div style="background-color: #ffeeee; padding: 10px; margin-bottom: 20px; border-radius: 5px;">'
            '<strong>Notice:</strong> This report has been sanitized for security and privacy reasons.'
            '</div>\n'
        )
        
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w") as f:
            f.write(sanitized_content)
            
        logger.info(f"Sanitized HTML saved to: {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error sanitizing HTML: {str(e)}")
        return False


def main() -> int:
    """
    Parse command line arguments and sanitize HTML file.

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(description="Sanitize HTML trade report")
    parser.add_argument("--input", required=True, help="Path to input HTML file")
    parser.add_argument("--output", required=True, help="Path to output sanitized HTML file")
    
    args = parser.parse_args()
    
    if sanitize_html(args.input, args.output):
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
