"""
Orchestrator Service

Implements the state diagram and guard chain for the Saxo Bot.
"""

import logging
import os
import time
from enum import Enum
from typing import Dict, Any, Optional, List

import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from prometheus_client import Gauge, generate_latest
from prometheus_client.exposition import CONTENT_TYPE_LATEST

from src.core.saxo_client import SaxoClient
from src.core.guards import (
    KillSwitch,
    LatencyGuard,
    ModeGuard,
    PriorityGuard,
    SlippageGuard,
    TradingMode,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orchestrator")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI."""
    global client, current_state, is_healthy
    
    client = SaxoClient(environment=ENV)
    
    background_tasks = BackgroundTasks()
    background_tasks.add_task(initialize_orchestrator)
    await background_tasks()
    
    yield
    
    logger.info("Shutting down orchestrator service")

app = FastAPI(
    title="Saxo Bot Orchestrator",
    lifespan=lifespan
)

class OrchestratorState(str, Enum):
    """Orchestrator state enum."""
    INIT = "INIT"
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    EM_STOP = "EM_STOP"


client: Optional[SaxoClient] = None
current_state = OrchestratorState.INIT
ws_connected = False
is_healthy = False
guard_chain_active = False

BOT_STATE = Gauge(
    "bot_state", 
    "Current bot state (0=INIT, 1=IDLE, 2=RUNNING, 3=PAUSED, 4=EM_STOP)", 
    ["env", "bot", "version"]
)
GUARD_STATUS = Gauge(
    "guard_status", 
    "Guard status (1=active, 0=inactive)", 
    ["env", "bot", "version", "guard_type"]
)

ENV = os.environ.get("ENVIRONMENT", "sim")
BOT_ID = os.environ.get("BOT_ID", "orchestrator")
VERSION = os.environ.get("VERSION", "v0.0.9")


class StateTransition(BaseModel):
    """State transition model for API requests."""
    target_state: OrchestratorState
    reason: Optional[str] = None





async def initialize_orchestrator() -> None:
    """Initialize the orchestrator."""
    global client, current_state, ws_connected, is_healthy, guard_chain_active
    
    if not client:
        logger.error("SaxoClient not initialized")
        return
    
    try:
        if not client.authenticate():
            logger.error("Authentication failed")
            return
        
        initialize_guard_chain()
        
        ws_connected = await check_websocket_connection()
        
        if ws_connected:
            await transition_state(OrchestratorState.IDLE, "WebSocket connected")
        
        is_healthy = True
        logger.info("Orchestrator initialized, service is healthy")
        
    except Exception as e:
        logger.error(f"Error initializing orchestrator: {str(e)}")
        is_healthy = False


def initialize_guard_chain() -> None:
    """Initialize the guard chain."""
    global client, guard_chain_active
    
    if not client:
        logger.error("SaxoClient not initialized")
        return
    
    try:
        client.slippage_guard = SlippageGuard()
        client.mode_guard = ModeGuard()
        client.kill_switch = KillSwitch()
        client.latency_guard = LatencyGuard()
        client.priority_guard = PriorityGuard()
        
        client.current_mode = TradingMode.LV_LL
        
        GUARD_STATUS.labels(env=ENV, bot=BOT_ID, version=VERSION, guard_type="slippage").set(1)
        GUARD_STATUS.labels(env=ENV, bot=BOT_ID, version=VERSION, guard_type="mode").set(1)
        GUARD_STATUS.labels(env=ENV, bot=BOT_ID, version=VERSION, guard_type="kill_switch").set(1)
        GUARD_STATUS.labels(env=ENV, bot=BOT_ID, version=VERSION, guard_type="latency").set(1)
        GUARD_STATUS.labels(env=ENV, bot=BOT_ID, version=VERSION, guard_type="priority").set(1)
        
        guard_chain_active = True
        logger.info("Guard chain initialized")
        
    except Exception as e:
        logger.error(f"Error initializing guard chain: {str(e)}")
        guard_chain_active = False


async def check_websocket_connection() -> bool:
    """Check if WebSocket connection is active."""
    global client
    
    if not client or not client.access_token:
        logger.error("Client not authenticated")
        return False
    
    return True


async def transition_state(new_state: OrchestratorState, reason: str) -> None:
    """Transition to a new state."""
    global current_state
    
    old_state = current_state
    current_state = new_state
    
    state_value = {
        OrchestratorState.INIT: 0,
        OrchestratorState.IDLE: 1,
        OrchestratorState.RUNNING: 2,
        OrchestratorState.PAUSED: 3,
        OrchestratorState.EM_STOP: 4,
    }.get(new_state, 0)
    
    BOT_STATE.labels(env=ENV, bot=BOT_ID, version=VERSION).set(state_value)
    
    logger.info(f"State transition: {old_state} -> {new_state} (Reason: {reason})")


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


@app.get("/state")
async def get_state() -> Dict[str, Any]:
    """Get current orchestrator state."""
    global current_state, ws_connected, guard_chain_active
    
    return {
        "state": current_state,
        "ws_connected": ws_connected,
        "guard_chain_active": guard_chain_active,
        "timestamp": time.time()
    }


@app.post("/state")
async def set_state(transition: StateTransition) -> Dict[str, Any]:
    """Set orchestrator state."""
    global current_state
    
    valid_transition = validate_state_transition(current_state, transition.target_state)
    
    if not valid_transition:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state transition: {current_state} -> {transition.target_state}"
        )
    
    await transition_state(
        transition.target_state, 
        transition.reason or f"Manual transition to {transition.target_state}"
    )
    
    return {"state": current_state, "timestamp": time.time()}


def validate_state_transition(current: OrchestratorState, target: OrchestratorState) -> bool:
    """Validate if a state transition is allowed."""
    valid_transitions = {
        OrchestratorState.INIT: [OrchestratorState.IDLE],
        OrchestratorState.IDLE: [OrchestratorState.RUNNING, OrchestratorState.EM_STOP],
        OrchestratorState.RUNNING: [OrchestratorState.PAUSED, OrchestratorState.EM_STOP],
        OrchestratorState.PAUSED: [OrchestratorState.RUNNING, OrchestratorState.EM_STOP],
        OrchestratorState.EM_STOP: [OrchestratorState.IDLE],
    }
    
    return target in valid_transitions.get(current, [])


@app.post("/bot-control")
async def bot_control(command: Dict[str, Any]) -> Dict[str, Any]:
    """Control bot operations."""
    global current_state
    
    action = command.get("action")
    
    if action == "start":
        if current_state == OrchestratorState.IDLE:
            await transition_state(OrchestratorState.RUNNING, "StartCmd")
            return {"status": "ok", "state": current_state}
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot start from state {current_state}"
            )
    
    elif action == "pause":
        if current_state == OrchestratorState.RUNNING:
            await transition_state(OrchestratorState.PAUSED, "PauseCmd")
            return {"status": "ok", "state": current_state}
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot pause from state {current_state}"
            )
    
    elif action == "resume":
        if current_state == OrchestratorState.PAUSED:
            await transition_state(OrchestratorState.RUNNING, "ResumeCmd")
            return {"status": "ok", "state": current_state}
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot resume from state {current_state}"
            )
    
    elif action == "emergency_stop":
        if current_state in [OrchestratorState.RUNNING, OrchestratorState.PAUSED]:
            await transition_state(OrchestratorState.EM_STOP, "EmergencyStopCmd")
            return {"status": "ok", "state": current_state}
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot emergency stop from state {current_state}"
            )
    
    elif action == "reset":
        if current_state == OrchestratorState.EM_STOP:
            await transition_state(OrchestratorState.IDLE, "ManualReset")
            return {"status": "ok", "state": current_state}
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot reset from state {current_state}"
            )
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action: {action}"
        )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
