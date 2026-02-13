"""Transport layer abstraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, Dict
from enum import Enum


class TransportError(Exception):
    """Transport layer error."""
    pass


@dataclass
class TransportConfig:
    """Transport configuration."""
    protocol: str = "websocket"
    timeout_ms: int = 5000
    retry_count: int = 3
    compression: bool = False
    buffer_size: int = 4096


class Transport(ABC):
    """Abstract transport layer."""
    
    def __init__(self, config: Optional[TransportConfig] = None):
        self.config = config or TransportConfig()
        self.connected = False
    
    @abstractmethod
    async def connect(self, address: str) -> None:
        """Connect to remote address."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect."""
        pass
    
    @abstractmethod
    async def send(self, data: Any) -> None:
        """Send data."""
        pass
    
    @abstractmethod
    async def receive(self) -> Any:
        """Receive data."""
        pass
    
    async def close(self) -> None:
        """Close transport."""
        await self.disconnect()


class WebSocketTransport(Transport):
    """WebSocket transport implementation."""
    
    async def connect(self, address: str) -> None:
        """Connect via WebSocket."""
        # Placeholder - would use aiohttp/websockets
        self.connected = True
    
    async def disconnect(self) -> None:
        """Disconnect WebSocket."""
        self.connected = False
    
    async def send(self, data: Any) -> None:
        """Send via WebSocket."""
        if not self.connected:
            raise TransportError("Not connected")
    
    async def receive(self) -> Any:
        """Receive via WebSocket."""
        if not self.connected:
            raise TransportError("Not connected")
        return None


class HTTPTransport(Transport):
    """HTTP transport implementation."""
    
    async def connect(self, address: str) -> None:
        """Setup HTTP connection."""
        self.connected = True
    
    async def disconnect(self) -> None:
        """Cleanup HTTP."""
        self.connected = False
    
    async def send(self, data: Any) -> None:
        """Send via HTTP."""
        if not self.connected:
            raise TransportError("Not connected")
    
    async def receive(self) -> Any:
        """Receive via HTTP."""
        if not self.connected:
            raise TransportError("Not connected")
        return None
