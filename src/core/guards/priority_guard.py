"""
PriorityGuard module.

This module provides the PriorityGuard class for managing bot priority and resource allocation.
"""

import logging
from enum import Enum

logger = logging.getLogger("saxo")


class BotPriority(Enum):
    """Bot priority levels."""

    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class BotState(Enum):
    """Bot operational states."""

    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


class PriorityGuard:
    """Manage bot priority and resource allocation."""

    def __init__(self) -> None:
        """Initialize the PriorityGuard."""
        self.bots: dict[str, tuple[BotPriority, BotState]] = {}

    def register_bot(self, bot_id: str, priority: BotPriority) -> None:
        """
        Register a bot with its priority.

        Args:
            bot_id: Unique identifier for the bot
            priority: Priority level of the bot
        """
        self.bots[bot_id] = (priority, BotState.STOPPED)
        logger.info(f"PriorityGuard: Registered bot {bot_id} with priority {priority.value}")

    def update_bot_state(self, bot_id: str, state: BotState) -> None:
        """
        Update a bot's operational state.

        Args:
            bot_id: Unique identifier for the bot
            state: New operational state of the bot
        """
        if bot_id not in self.bots:
            logger.warning(f"PriorityGuard: Bot {bot_id} not registered")
            return

        priority, _ = self.bots[bot_id]
        self.bots[bot_id] = (priority, state)
        logger.info(f"PriorityGuard: Bot {bot_id} state updated to {state.value}")

        self._apply_priority_rules()

    def get_bot_state(self, bot_id: str) -> BotState:
        """
        Get a bot's current operational state.

        Args:
            bot_id: Unique identifier for the bot

        Returns:
            BotState: Current operational state of the bot
        """
        if bot_id not in self.bots:
            logger.warning(f"PriorityGuard: Bot {bot_id} not registered")
            return BotState.STOPPED

        _, state = self.bots[bot_id]
        return state

    def _apply_priority_rules(self) -> None:
        """
        Apply priority rules to manage bot operations.

        As per specification:
        When the upper Priority is RUNNING, the lower BOT is automatically
        reduced from max 1 to 0 process.
        """
        high_running = any(
            state == BotState.RUNNING
            for priority, state in self.bots.values()
            if priority == BotPriority.HIGH
        )

        if high_running:
            for bot_id, (priority, state) in list(self.bots.items()):
                if priority in (BotPriority.NORMAL, BotPriority.LOW) and state == BotState.RUNNING:
                    self.bots[bot_id] = (priority, BotState.PAUSED)
                    logger.info(
                        f"PriorityGuard: Paused {priority.value} priority bot {bot_id} "
                        f"due to HIGH priority bot running"
                    )

        normal_running = any(
            state == BotState.RUNNING
            for priority, state in self.bots.values()
            if priority == BotPriority.NORMAL
        )

        if normal_running:
            for bot_id, (priority, state) in list(self.bots.items()):
                if priority == BotPriority.LOW and state == BotState.RUNNING:
                    self.bots[bot_id] = (priority, BotState.PAUSED)
                    logger.info(
                        f"PriorityGuard: Paused LOW priority bot {bot_id} "
                        f"due to NORMAL priority bot running"
                    )
