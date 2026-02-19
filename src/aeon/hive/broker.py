import json
from typing import List, Dict, Any, Optional
from aeon.hive.protocol import HiveAdapter, A2AConfig
from aeon.core.packet import Packet, PacketType

class A2ABroker:
    """
    Hive Layer (L4) Component for Swarm Discovery and Orchestration.
    Connects Agents based on their SOUL.md roles and managing the 'Hiring' flow.
    """
    
    def __init__(self, hive_adapter: HiveAdapter):
        self.hive = hive_adapter
        self.registry: Dict[str, Dict[str, Any]] = {} # Node ID -> Metadata

    def register_node(self, node_id: str, role: str, capabilities: List[str]):
        """Registers a discovered node into the local swarm registry."""
        self.registry[node_id] = {
            "role": role,
            "capabilities": capabilities,
            "status": "online"
        }
        print(f" [i] Hive: Discovered agent '{node_id}' with role '{role}'")

    def find_worker(self, required_role: str) -> Optional[str]:
        """Finds the best worker for a specific role."""
        for node_id, meta in self.registry.items():
            if meta["role"] == required_role and meta["status"] == "online":
                return node_id
        return None

    async def hire_agent(self, manager_id: str, worker_id: str, goal: str) -> Packet:
        """
        Initiates a 'Hiring' handshake between a Manager and a Worker.
        Returns a formal REQUEST packet to be sent via the Hive.
        """
        packet = Packet.create_request(
            sender=manager_id,
            receiver=worker_id,
            activity="swarm_task",
            params={"goal": goal, "context_id": f"ctx_{manager_id[:4]}"}
        )
        print(f" [>] Swarm: Manager '{manager_id}' hiring Worker '{worker_id}' for goal: {goal}")
        return packet
