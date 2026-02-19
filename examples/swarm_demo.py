import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from aeon.hive.broker import A2ABroker
from aeon.hive.protocol import HiveAdapter, A2AConfig
from aeon.core.vault.checkpoint import SwarmCheckpoint
from aeon.core.packet import Packet

async def main():
    print("="*60)
    print(" ÆON SWARM DEMO: PERSISTENT MULTI-AGENT ORCHESTRATION")
    print("="*60)

    # 1. Initialize Components
    hive = HiveAdapter(A2AConfig(role="manager"))
    broker = A2ABroker(hive)
    checkpoint = SwarmCheckpoint()

    # 2. Simulate Discovery (The CrewAI Paradigm)
    print("\n [Step 1] Discovering Agents...")
    broker.register_node("agnet_bravo", "TravelAgent", ["flight_booking", "hotel_search"])
    broker.register_node("agnet_charlie", "LocalGuide", ["restaurant_recommendation"])

    worker_id = broker.find_worker("TravelAgent")
    print(f" [i] Manager selected '{worker_id}' for the trip planning mission.")

    # 3. Persistent Loop (The LangGraph Paradigm)
    print("\n [Step 2] Initiating Task with Persistence...")
    
    goal = "Plan a 3-day trip to Tokyo."
    current_state = {
        "swarm_id": "tokyo_trip_01",
        "manager": "Alpha",
        "worker": worker_id,
        "goal": goal,
        "step": 1,
        "completed": False
    }

    # Save initial state
    checkpoint.save_snapshot(current_state["swarm_id"], current_state)

    # 4. Hierarchical Hiring (A2A Protocol)
    print("\n [Step 3] Hiring Worker via A2A Packet...")
    packet = await broker.hire_agent("AlphaAgent", worker_id, goal)
    
    print(f" [>] Packet ID: {packet.header.packet_id}")
    print(f" [>] Payload: {packet.payload['goal']}")

    # 5. Simulate Progress & Update State
    print("\n [Step 4] Simulating Task Progress...")
    await asyncio.sleep(1)
    
    current_state["step"] = 2
    current_state["progress"] = "Flight options found: NH123, JL456"
    checkpoint.save_snapshot(current_state["swarm_id"], current_state)

    print("\n [✓] Swarm Demo Complete. All states persisted in the Vault.")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
