"""
Provider: Base transport abstraction for external platforms.
Follows Protocol-Oriented Design for maximum extensibility.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, AsyncIterator
from pydantic import BaseModel
from enum import Enum


class TransportType(str, Enum):
    """Transport protocol types."""
    SYNC = "sync"
    ASYNC = "async"
    WEBHOOK = "webhook"
    POLLING = "polling"


class ProviderConfig(BaseModel):
    """Base configuration for transport providers."""
    transport_type: TransportType = TransportType.ASYNC
    timeout: int = 30
    retry_count: int = 3
    enabled: bool = True
    metadata: Dict[str, Any] = {}


class Packet(BaseModel):
    """Data packet for inter-platform communication."""
    origin: str  # Source platform identifier
    destination: str  # Target recipient
    payload: str  # Message content
    metadata: Dict[str, Any] = {}


class IntegrationProvider(ABC):
    """
    Abstract transport provider for platform integration.
    Implementations handle bidirectional communication with external systems.
    """

    def __init__(self, config: ProviderConfig):
        self.config = config
        self._initialized = False

    @abstractmethod
    async def dispatch(self, packet: Packet) -> bool:
        """
        Send a packet to the external platform.
        Returns True if successful, False otherwise.
        """
        pass

    @abstractmethod
    async def receive(self) -> Optional[Packet]:
        """
        Poll for incoming packets from the external platform.
        Returns None if no packets available.
        """
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the transport connection."""
        pass

    @abstractmethod
    async def terminate(self) -> None:
        """Gracefully terminate the connection."""
        pass

    async def health_check(self) -> bool:
        """Verify provider connectivity and health."""
        return self._initialized
