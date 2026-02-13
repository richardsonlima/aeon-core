"""Core gateway implementation."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GatewayState(Enum):
    """Gateway operational states."""
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    SHUTDOWN = "shutdown"


@dataclass
class GatewayConfig:
    """Gateway configuration."""
    host: str = "127.0.0.1"
    port: int = 8000
    bind_address: Optional[str] = None
    max_connections: int = 1000
    request_timeout_ms: int = 30000
    session_ttl_seconds: int = 3600
    enable_compression: bool = True
    enable_encryption: bool = False
    max_message_size_mb: int = 10
    metrics_enabled: bool = True
    health_check_interval_ms: int = 30000


class Gateway:
    """
    Central gateway managing agent communication and coordination.
    
    Responsibilities:
    - Connection management
    - Message routing
    - Session persistence
    - Health monitoring
    - Rate limiting
    - Resource management
    """
    
    def __init__(self, config: Optional[GatewayConfig] = None):
        self.config = config or GatewayConfig()
        self.state = GatewayState.INITIALIZING
        self.connections: Dict[str, Any] = {}
        self.stats = {
            "total_messages": 0,
            "total_connections": 0,
            "active_connections": 0,
            "messages_per_second": 0,
            "uptime_seconds": 0,
            "errors": 0
        }
        self.created_at = datetime.utcnow()
    
    async def initialize(self) -> None:
        """Initialize gateway."""
        logger.info(f"Initializing gateway on {self.config.host}:{self.config.port}")
        self.state = GatewayState.READY
    
    async def start(self) -> None:
        """Start gateway."""
        if self.state not in (GatewayState.READY, GatewayState.MAINTENANCE):
            raise RuntimeError(f"Cannot start from state {self.state}")
        
        logger.info("Starting gateway")
        self.state = GatewayState.RUNNING
    
    async def stop(self) -> None:
        """Stop gateway."""
        logger.info("Stopping gateway")
        await self._close_all_connections()
        self.state = GatewayState.SHUTDOWN
    
    async def _close_all_connections(self) -> None:
        """Close all active connections."""
        for conn_id, conn in list(self.connections.items()):
            try:
                if hasattr(conn, 'close'):
                    await conn.close()
            except Exception as e:
                logger.error(f"Error closing connection {conn_id}: {e}")
            finally:
                del self.connections[conn_id]
    
    async def register_connection(self, connection_id: str, connection: Any) -> None:
        """Register a new connection."""
        if len(self.connections) >= self.config.max_connections:
            raise RuntimeError("Max connections reached")
        
        self.connections[connection_id] = connection
        self.stats["total_connections"] += 1
        self.stats["active_connections"] = len(self.connections)
        logger.debug(f"Connection registered: {connection_id}")
    
    async def unregister_connection(self, connection_id: str) -> None:
        """Unregister a connection."""
        if connection_id in self.connections:
            del self.connections[connection_id]
            self.stats["active_connections"] = len(self.connections)
            logger.debug(f"Connection unregistered: {connection_id}")
    
    async def send_message(self, connection_id: str, message: Any) -> None:
        """Send message through connection."""
        if connection_id not in self.connections:
            raise ValueError(f"Unknown connection: {connection_id}")
        
        connection = self.connections[connection_id]
        self.stats["total_messages"] += 1
        
        try:
            await connection.send(message)
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Error sending message: {e}")
            raise
    
    def get_state(self) -> Dict[str, Any]:
        """Get gateway state."""
        uptime = (datetime.utcnow() - self.created_at).total_seconds()
        return {
            "state": self.state.value,
            "config": {
                "host": self.config.host,
                "port": self.config.port,
                "max_connections": self.config.max_connections
            },
            "stats": {
                **self.stats,
                "uptime_seconds": uptime,
                "active_connections": len(self.connections)
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            "healthy": self.state in (GatewayState.READY, GatewayState.RUNNING),
            "state": self.state.value,
            "connections": len(self.connections),
            "errors": self.stats["errors"]
        }
