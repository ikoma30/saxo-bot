"""
Tests for the Orchestrator service.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

from src.services.orchestrator.main import (
    app,
    OrchestratorState,
    transition_state,
    validate_state_transition,
    initialize_guard_chain,
)


class TestOrchestratorService:
    """Tests for the Orchestrator service."""

    def setup_method(self) -> None:
        """Set up test method."""
        self.client = TestClient(app)

    @pytest.mark.asyncio
    async def test_transition_state(self) -> None:
        """Test state transitions."""
        await transition_state(OrchestratorState.IDLE, "Test transition")
        from src.services.orchestrator.main import current_state
        assert current_state == OrchestratorState.IDLE

    def test_validate_state_transition(self) -> None:
        """Test state transition validation."""
        assert validate_state_transition(OrchestratorState.INIT, OrchestratorState.IDLE) is True
        assert validate_state_transition(OrchestratorState.IDLE, OrchestratorState.RUNNING) is True
        assert validate_state_transition(OrchestratorState.RUNNING, OrchestratorState.PAUSED) is True
        assert validate_state_transition(OrchestratorState.PAUSED, OrchestratorState.RUNNING) is True
        assert validate_state_transition(OrchestratorState.RUNNING, OrchestratorState.EM_STOP) is True
        assert validate_state_transition(OrchestratorState.EM_STOP, OrchestratorState.IDLE) is True

        assert validate_state_transition(OrchestratorState.INIT, OrchestratorState.RUNNING) is False
        assert validate_state_transition(OrchestratorState.IDLE, OrchestratorState.PAUSED) is False
        assert validate_state_transition(OrchestratorState.EM_STOP, OrchestratorState.RUNNING) is False

    def test_healthz_endpoint(self) -> None:
        """Test healthz endpoint."""
        with patch("src.services.orchestrator.main.is_healthy", True):
            response = self.client.get("/healthz")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

        with patch("src.services.orchestrator.main.is_healthy", False):
            response = self.client.get("/healthz")
            assert response.status_code == 503
            assert response.json() == {"status": "error"}

    def test_initialize_guard_chain(self) -> None:
        """Test guard chain initialization."""
        with patch("src.services.orchestrator.main.client") as mock_client:
            initialize_guard_chain()
            
            assert hasattr(mock_client, "slippage_guard")
            assert hasattr(mock_client, "mode_guard")
            assert hasattr(mock_client, "kill_switch")
            assert hasattr(mock_client, "latency_guard")
            assert hasattr(mock_client, "priority_guard")
