"""
Streaming Subscriber Service

Subscribes to Saxo Bank activities and trades streams and persists them.
"""

import logging
import os
import sqlite3
import time
from typing import Dict, Any, List, Optional

import aiohttp
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import websockets
from prometheus_client import Counter, Gauge, generate_latest
from prometheus_client.exposition import CONTENT_TYPE_LATEST

from src.core.saxo_client import SaxoClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("subscriber")

app = FastAPI(title="Saxo Streaming Subscriber")

client: Optional[SaxoClient] = None
db_conn: Optional[sqlite3.Connection] = None
ws_connection: Optional[Any] = None  # WebSocket connection
context_id: Optional[str] = None
subscription_ids: List[str] = []
is_healthy = False

TRADE_FILLS = Counter(
    "trade_fill_total", 
    "Total number of trade fills", 
    ["env", "bot", "version", "instrument"]
)
ACTIVITY_COUNT = Counter(
    "activity_total", 
    "Total number of activities", 
    ["env", "bot", "version", "type"]
)
SUBSCRIPTION_STATUS = Gauge(
    "subscription_status", 
    "Subscription status (1=active, 0=inactive)", 
    ["env", "bot", "version", "type"]
)

ENV = os.environ.get("ENVIRONMENT", "sim")
BOT_ID = os.environ.get("BOT_ID", "subscriber")
VERSION = os.environ.get("VERSION", "v0.0.9")


class Trade(BaseModel):
    """Trade model for API responses."""
    order_id: str
    instrument: str
    side: str
    amount: float
    fill_price: float
    fill_time: str
    profit_loss: float


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize the service on startup."""
    global client, db_conn
    
    client = SaxoClient(environment=ENV)
    
    db_conn = sqlite3.connect("trades.db", check_same_thread=False)
    create_tables()
    
    background_tasks = BackgroundTasks()
    background_tasks.add_task(start_subscriptions)
    await background_tasks()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up resources on shutdown."""
    global client, db_conn, ws_connection
    
    if ws_connection:
        await ws_connection.close()
    
    if db_conn:
        db_conn.close()


def create_tables() -> None:
    """Create database tables if they don't exist."""
    global db_conn
    
    if not db_conn:
        logger.error("Database connection not initialized")
        return
    
    cursor = db_conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT NOT NULL,
        instrument TEXT NOT NULL,
        side TEXT NOT NULL,
        amount REAL NOT NULL,
        fill_price REAL NOT NULL,
        fill_time TEXT NOT NULL,
        profit_loss REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        activity_id TEXT NOT NULL,
        activity_type TEXT NOT NULL,
        activity_time TEXT NOT NULL,
        instrument TEXT,
        description TEXT,
        data TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    db_conn.commit()


async def start_subscriptions() -> None:
    """Start WebSocket subscriptions for activities and trades."""
    global client, ws_connection, context_id, subscription_ids, is_healthy
    
    if not client:
        logger.error("SaxoClient not initialized")
        return
    
    try:
        if not client.authenticate():
            logger.error("Authentication failed")
            return
        
        context_id = f"subscriber-{int(time.time())}"
        
        activities_subscription = await subscribe_to_activities()
        if activities_subscription:
            subscription_ids.append(activities_subscription.get("ContextId", ""))
            SUBSCRIPTION_STATUS.labels(env=ENV, bot=BOT_ID, version=VERSION, type="activities").set(1)
        
        trades_subscription = await subscribe_to_trades()
        if trades_subscription:
            subscription_ids.append(trades_subscription.get("ContextId", ""))
            SUBSCRIPTION_STATUS.labels(env=ENV, bot=BOT_ID, version=VERSION, type="trades").set(1)
        
        await connect_to_websocket()
        
        if subscription_ids and ws_connection:
            is_healthy = True
            logger.info("Subscriptions active, service is healthy")
        
    except Exception as e:
        logger.error(f"Error starting subscriptions: {str(e)}")
        is_healthy = False


async def subscribe_to_activities() -> Dict[str, Any]:
    """Subscribe to activities stream."""
    global client, context_id
    
    if not client or not client.access_token:
        logger.error("Client not authenticated")
        return {}
    
    headers = {"Authorization": f"Bearer {client.access_token}"}
    url = f"{client.base_url}/ens/v1/activities/subscriptions"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            headers=headers,
            json={"ContextId": context_id, "ReferenceId": "activities-subscription"},
            timeout=client.timeout
        ) as response:
            if response.status != 201:
                logger.error(f"Failed to subscribe to activities: {response.status}")
                return {}
            
            data = await response.json()
            logger.info(f"Subscribed to activities: {data}")
            return data


async def subscribe_to_trades() -> Dict[str, Any]:
    """Subscribe to trades stream."""
    global client, context_id
    
    if not client or not client.access_token:
        logger.error("Client not authenticated")
        return {}
    
    headers = {"Authorization": f"Bearer {client.access_token}"}
    url = f"{client.base_url}/port/v1/trades/subscriptions"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            headers=headers,
            json={"ContextId": context_id, "ReferenceId": "trades-subscription"},
            timeout=client.timeout
        ) as response:
            if response.status != 201:
                logger.error(f"Failed to subscribe to trades: {response.status}")
                return {}
            
            data = await response.json()
            logger.info(f"Subscribed to trades: {data}")
            return data


async def connect_to_websocket() -> None:
    """Connect to Saxo Bank WebSocket."""
    global client, ws_connection, context_id
    
    if not client or not client.access_token or not context_id:
        logger.error("Client not authenticated or context ID not set")
        return
    
    ws_url = f"{client.base_url.replace('https://', 'wss://')}/streaming/connection?contextId={context_id}"
    
    try:
        ws_connection = await websockets.connect(
            ws_url,
            extra_headers={"Authorization": f"Bearer {client.access_token}"}
        )
        
        background_tasks = BackgroundTasks()
        background_tasks.add_task(listen_for_messages)
        await background_tasks()
        
    except Exception as e:
        logger.error(f"WebSocket connection error: {str(e)}")
        ws_connection = None


async def listen_for_messages() -> None:
    """Listen for WebSocket messages."""
    global ws_connection, db_conn
    
    if not ws_connection:
        logger.error("WebSocket connection not established")
        return
    
    if not db_conn:
        logger.error("Database connection not initialized")
        return
    
    try:
        async for message in ws_connection:
            try:
                data = message.json()
                
                if "ReferenceId" in data:
                    if data["ReferenceId"] == "activities-subscription":
                        await process_activity(data)
                    elif data["ReferenceId"] == "trades-subscription":
                        await process_trade(data)
                
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
    
    except Exception as e:
        logger.error(f"WebSocket listening error: {str(e)}")
        await connect_to_websocket()


async def process_activity(data: Dict[str, Any]) -> None:
    """Process an activity message."""
    global db_conn
    
    if not db_conn:
        logger.error("Database connection not initialized")
        return
    
    try:
        activity_data = data.get("Data", {})
        activity_id = activity_data.get("ActivityId", "")
        activity_type = activity_data.get("ActivityType", "")
        activity_time = activity_data.get("Timestamp", "")
        instrument = activity_data.get("Instrument", {}).get("Symbol", "")
        description = activity_data.get("Description", "")
        
        cursor = db_conn.cursor()
        cursor.execute(
            """
            INSERT INTO activities (
                activity_id, activity_type, activity_time, 
                instrument, description, data
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                activity_id, activity_type, activity_time,
                instrument, description, str(data)
            )
        )
        db_conn.commit()
        
        ACTIVITY_COUNT.labels(
            env=ENV, bot=BOT_ID, version=VERSION, type=activity_type
        ).inc()
        
        logger.info(f"Processed activity: {activity_id} ({activity_type})")
    
    except Exception as e:
        logger.error(f"Error processing activity: {str(e)}")


async def process_trade(data: Dict[str, Any]) -> None:
    """Process a trade message."""
    global db_conn
    
    if not db_conn:
        logger.error("Database connection not initialized")
        return
    
    try:
        trade_data = data.get("Data", {})
        order_id = trade_data.get("OrderId", "")
        instrument = trade_data.get("Instrument", {}).get("Symbol", "")
        side = trade_data.get("BuySell", "")
        amount = float(trade_data.get("Amount", 0))
        fill_price = float(trade_data.get("Price", 0))
        fill_time = trade_data.get("Timestamp", "")
        profit_loss = float(trade_data.get("ProfitLoss", {}).get("Amount", 0))
        
        cursor = db_conn.cursor()
        cursor.execute(
            """
            INSERT INTO trades (
                order_id, instrument, side, 
                amount, fill_price, fill_time, profit_loss
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_id, instrument, side,
                amount, fill_price, fill_time, profit_loss
            )
        )
        db_conn.commit()
        
        TRADE_FILLS.labels(
            env=ENV, bot=BOT_ID, version=VERSION, instrument=instrument
        ).inc()
        
        logger.info(f"Processed trade: {order_id} ({instrument})")
    
    except Exception as e:
        logger.error(f"Error processing trade: {str(e)}")


@app.get("/healthz")
async def healthz() -> JSONResponse:
    """Health check endpoint."""
    if is_healthy:
        return JSONResponse(content={"status": "ok"})
    else:
        return JSONResponse(content={"status": "error"}, status_code=503)


@app.get("/metrics")
async def metrics() -> JSONResponse:
    """Prometheus metrics endpoint."""
    return JSONResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/internal/trades")
async def get_trades() -> List[Trade]:
    """Get recent trades."""
    global db_conn
    
    if not db_conn:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    cursor = db_conn.cursor()
    cursor.execute(
        """
        SELECT order_id, instrument, side, amount, fill_price, fill_time, profit_loss
        FROM trades
        ORDER BY fill_time DESC
        LIMIT 100
        """
    )
    
    trades = []
    for row in cursor.fetchall():
        trades.append(
            Trade(
                order_id=row[0],
                instrument=row[1],
                side=row[2],
                amount=row[3],
                fill_price=row[4],
                fill_time=row[5],
                profit_loss=row[6]
            )
        )
    
    return trades


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8081, reload=False)
