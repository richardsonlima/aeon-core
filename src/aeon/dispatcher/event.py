"""
Event Definitions: Type-safe event representation.
Supports event hierarchy and contextual metadata.
"""

from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel
from enum import Enum


class EventType(str, Enum):
    """System event classifications."""
    LIFECYCLE_BOOT = "lifecycle.boot"
    LIFECYCLE_SHUTDOWN = "lifecycle.shutdown"
    COMMUNICATION_RECEIVED = "communication.received"
    COMMUNICATION_SENT = "communication.sent"
    PROCESSING_START = "processing.start"
    PROCESSING_COMPLETE = "processing.complete"
    ERROR_OCCURRED = "error.occurred"
    CAPABILITY_LOADED = "capability.loaded"
    CAPABILITY_FAILED = "capability.failed"


class Event(BaseModel):
    """
    Type-safe event representation.
    Carries event metadata, payload, and source information.
    """
    event_type: EventType
    timestamp: datetime
    source: str  # Component that emitted the event
    payload: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    priority: int = 0  # Higher = more important

    def is_critical(self) -> bool:
        """Check if event represents a critical condition."""
        return "error" in self.event_type.value or self.priority > 10
