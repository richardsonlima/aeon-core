import sys
import os
import asyncio

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from aeon.hive.broker import A2ABroker
from aeon.hive.protocol import HiveAdapter, A2AConfig
from aeon.core.vault.checkpoint import SwarmCheckpoint

async def verify_swarm_intelligence():
    print(" [~] Initiating Æon Swarm (Hive) Verification...")
    
    # 1. Test Role-Based Discovery
    print("\n [1] Testing Role-Based Discovery (CrewAI Paradigm):")
    hive = HiveAdapter(A2AConfig(role="manager"))
    broker = A2ABroker(hive)
    
    broker.register_node("agnet_01", "Researcher", ["web_search", "arxiv"])
    broker.register_node("agnet_02", "Writer", ["markdown_export"])
    
    worker = broker.find_worker("Researcher")
    if worker == "agnet_01":
        print("     [OK] Correct worker identified by SOUL.md Role.")
    else:
        print("     [FAIL] Role discovery failed.")

    # 2. Test Hiring Handshake
    print("\n [2] Testing Swarm Handshake (Packet-based):")
    packet = await broker.hire_agent("ManagerAgent", "agnet_01", "Research LangGraph vs Æon")
    if packet.header.packet_type == "request" and packet.payload["activity"] == "swarm_task":
        print("     [OK] Hiring packet successfully generated with structured payload.")
    else:
        print("     [FAIL] Handshake protocol violation.")

    # 3. Test Persistence (LangGraph Paradigm)
    print("\n [3] Testing State Persistence (Vault Checkpoints):")
    checkpoint = SwarmCheckpoint()
    state = {
        "active_agents": ["Manager", "Researcher"],
        "current_task": "Research LangGraph vs Æon",
        "pending_packets": 2,
        "history": ["Handshake complete"]
    }
    
    path = checkpoint.save_snapshot("swarm_99", state)
    restored = checkpoint.load_latest("swarm_99")
    
    if restored and restored["current_task"] == state["current_task"]:
        print(f"     [OK] Swarm state successfully persisted to Vault: {os.path.basename(path)}")
    else:
        print("     [FAIL] State restoration failed.")

    print("\n [✓] Swarm Hive & Persistence Verification Complete!")

if __name__ == "__main__":
    asyncio.run(verify_swarm_intelligence())
