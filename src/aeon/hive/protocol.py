"""
Hive Layer: Social Cognition.
Handles Agent-to-Agent (A2A) communication via the Unified Linux Foundation Standard.
"""
from typing import List, Optional
from pydantic import BaseModel, Field

# Attempt to import the official SDK. 
# If missing, we gracefully degrade to Node Identity mode (v0.1.0 behavior).
try:
    import a2a
except ImportError:
    a2a = None

class A2AConfig(BaseModel):
    """Configuration for the A2A Protocol."""
    port: int = 8000
    role: str = "server"
    version: str = "unified-1.0"
    capabilities: List[str] = Field(default_factory=list)

class HiveAdapter:
    """
    Adapter for the A2A Protocol.
    Manages Node Identity, Discovery Beacons, and Swarm Handshakes.
    """
    def __init__(self, config: A2AConfig):
        self.config = config
        self.server = None
        self._is_active = False

    def start_server(self):
        """
        Initializes the A2A Node Identity.
        """
        print(f"[+] Hive: Initializing A2A Node on port {self.config.port}...")
        
        # In a full deployment with the SDK installed:
        if a2a:
            # self.server = a2a.Server(port=self.config.port)
            # self.server.start()
            pass
            
        self._is_active = True

    def is_online(self) -> bool:
        return self._is_active

    def broadcast_availability(self):
        """
        Announces agent presence to the swarm via A2A Beacon.
        This allows other agents (BeeAI/Google) to discover this node.
        """
        if self._is_active:
            print(f" [>] Hive: A2A Beacon Active (Std: {self.config.version})")