"""
Dialogue Context: Conversation state representation.
Event-sourced approach to maintaining conversation semantics.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from enum import Enum


class ActorRole(str, Enum):
    """Participant role in dialogue."""
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


class Turn(BaseModel):
    """
    Single turn in a dialogue exchange.
    Captures speaker, content, timestamp, and contextual metadata.
    """
    actor: ActorRole
    utterance: str
    timestamp: datetime
    context_snapshot: Dict[str, Any] = {}
    annotations: Dict[str, Any] = {}


class DialogueContext(BaseModel):
    """
    Persistent dialogue context container.
    Maintains full conversation history with turn-level granularity.
    """
    context_id: str
    origin_platform: str  # e.g., "telegram", "slack"
    participant_id: str
    turns: List[Turn] = []
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = {}

    def add_turn(self, actor: ActorRole, utterance: str, **kwargs) -> None:
        """Append a new turn to the dialogue."""
        turn = Turn(
            actor=actor,
            utterance=utterance,
            timestamp=datetime.now(),
            **kwargs
        )
        self.turns.append(turn)
        self.updated_at = datetime.now()

    def get_history(self, limit: Optional[int] = None) -> List[Turn]:
        """Retrieve dialogue history, optionally limited to recent turns."""
        if limit is None:
            return self.turns
        return self.turns[-limit:]

    def get_last_turn(self) -> Optional[Turn]:
        """Get the most recent turn."""
        return self.turns[-1] if self.turns else None

    def clear_history(self) -> None:
        """Clear all turns from the context."""
        self.turns = []
        self.updated_at = datetime.now()
