#!/usr/bin/env python3
"""
Generate HTML report of Saxo trades.

This script queries the Saxo Bank API for trade data and generates an HTML report.
"""

import os
import sys
import datetime
import logging
from pathlib import Path

import pandas as pd

from src.core.saxo_client import SaxoClient

sys.path.append(str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("trade_report")


def generate_trade_report(environment: str = "sim") -> str:
    """
    Generate an HTML report of trades.
    
    Args:
        environment: Either "live" or "sim" for production or simulation environment
    
    Returns:
        str: Path to the generated HTML file
    """
    client = SaxoClient(environment=environment)
    
    if not client.authenticate():
        logger.error("Authentication failed, cannot generate trade report")
        return ""
    
    account_key = os.environ.get(f"{environment.upper()}_ACCOUNT_KEY")
    if not account_key:
        logger.error(f"Missing {environment.upper()}_ACCOUNT_KEY environment variable")
        return ""
    
    logger.info(f"Querying trades for account {account_key}")
    
    headers = client._get_headers()
    endpoint = f"/trade/v1/trades?AccountKey={account_key}"
    
    try:
        import requests
        response = requests.get(
            f"{client.base_url}{endpoint}",
            headers=headers,
            timeout=client.timeout,
        )
        response.raise_for_status()
        trades_data = response.json()
        
        if not trades_data or "Data" not in trades_data:
            logger.error("No trade data received from API")
            return ""
        
        trades_df = pd.DataFrame(trades_data["Data"])
        
        total_trades = len(trades_df)
        profitable_trades = len(trades_df[trades_df["ProfitLossInBaseCurrency"] > 0])
        loss_trades = len(trades_df[trades_df["ProfitLossInBaseCurrency"] <= 0])
        
        profit_factor = float("inf")
        if loss_trades > 0:
            profit_factor = profitable_trades / loss_trades
        
        summary_stats = {
            "Total Trades": total_trades,
            "Profitable Trades": profitable_trades,
            "Loss Trades": loss_trades,
            "Profit Factor": profit_factor
        }
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        html_path = f"reports/saxo_trades_{environment}_{timestamp}.html"
        
        os.makedirs(os.path.dirname(html_path), exist_ok=True)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Saxo Trade Report - {environment.upper()}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #0066cc; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                tr:hover {{ background-color: #f5f5f5; }}
                .summary {{ background-color: #e6f2ff; padding: 15px; border-radius: 5px; }}
                .download-link {{ margin-top: 20px; }}
                .download-link a {{ background-color: #4CAF50; color: white; padding: 10px 15px; 
                                   text-decoration: none; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <h1>Saxo Trade Report - {environment.upper()}</h1>
            <p>Generated on {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            
            <div class="summary">
                <h2>Summary Statistics</h2>
                <table>
                    <tr><th>Metric</th><th>Value</th></tr>
                    <tr><td>Total Trades</td><td>{summary_stats["Total Trades"]}</td></tr>
                    <tr><td>Profitable Trades</td><td>{summary_stats["Profitable Trades"]}</td></tr>
                    <tr><td>Loss Trades</td><td>{summary_stats["Loss Trades"]}</td></tr>
                    <tr><td>Profit Factor</td><td>{summary_stats["Profit Factor"]:.2f}</td></tr>
                </table>
            </div>
            
            <h2>Trade Details</h2>
            <table>
                <tr>
                    <th>Trade ID</th>
                    <th>Instrument</th>
                    <th>Buy/Sell</th>
                    <th>Open Price</th>
                    <th>Close Price</th>
                    <th>Volume</th>
                    <th>Profit/Loss</th>
                    <th>Open Time</th>
                    <th>Close Time</th>
                </tr>
        """
        
        for _, trade in trades_df.iterrows():
            profit_class = "profit" if trade.get("ProfitLossInBaseCurrency", 0) > 0 else "loss"
            html_content += f"""
                <tr class="{profit_class}">
                    <td>{trade.get("TradeId", "")}</td>
                    <td>{trade.get("DisplayName", "")}</td>
                    <td>{trade.get("BuySell", "")}</td>
                    <td>{trade.get("OpenPrice", "")}</td>
                    <td>{trade.get("ClosePrice", "")}</td>
                    <td>{trade.get("Amount", "")}</td>
                    <td>{trade.get("ProfitLossInBaseCurrency", "")}</td>
                    <td>{trade.get("OpenDate", "")}</td>
                    <td>{trade.get("CloseDate", "")}</td>
                </tr>
            """
        
        json_path = f"reports/saxo_trades_{environment}_{timestamp}.json"
        with open(json_path, "w") as f:
            import json
            json.dump(trades_data, f, indent=2)
        
        html_content += f"""
            </table>
            
            <div class="download-link">
                <a href="{os.path.basename(json_path)}" download>Download Raw JSON Data</a>
            </div>
        </body>
        </html>
        """
        
        with open(html_path, "w") as f:
            f.write(html_content)
        
        logger.info(f"Generated HTML report at {html_path}")
        logger.info(f"Raw JSON data saved at {json_path}")
        return html_path
        
    except Exception as e:
        logger.error(f"Error generating trade report: {str(e)}")
        return ""


if __name__ == "__main__":
    environment = "sim" if len(sys.argv) <= 1 else sys.argv[1]
    report_path = generate_trade_report(environment)
    
    if report_path:
        print(f"Report generated at: {report_path}")
        sys.exit(0)
    else:
        print("Failed to generate report")
        sys.exit(1)
