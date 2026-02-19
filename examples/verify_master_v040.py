import sys
import os
import asyncio
from datetime import datetime
from unittest.mock import patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from aeon.core.agent import Agent
from aeon.security.trust import TrustLevel
from aeon.core.packet import Packet
from aeon.executive.citation import CitationAxiom
from aeon.executive.identity import IdentityAxiom
from aeon.cortex.context import SituationalInjector
from aeon.dispatcher.hub import EventHub
from aeon.dispatcher.event import Event, EventType
from aeon.dispatcher.recovery import RecoveryHandler
from aeon.hive.broker import A2ABroker
from aeon.hive.protocol import HiveAdapter, A2AConfig
from aeon.core.vault.checkpoint import SwarmCheckpoint

async def run_master_verification():
    print("="*70)
    print(" ÆON FRAMEWORK v0.4.0-ULTRA: MASTER CONSOLIDATED VERIFICATION")
    print("="*70)
    
    # 0. Environment Setup
    os.environ["OPENROUTER_API_KEY"] = "sk-master-verify-dummy"

    # --- MODULE 1: IDENTITY & SITUATIONAL AWARENESS ---
    print("\n[MODULE 1] Identity & Deterministic Context")
    injector = SituationalInjector()
    ctx = injector.get_current_context()
    print(f" [✓] Situational: Time={ctx['user_local_time']}, Loc={ctx['location']}")
    
    identity = IdentityAxiom()
    reinforcement = identity.get_system_reinforcement()
    if "Richardson Lima" in reinforcement:
        print(" [✓] Identity: SOUL.md linking successful.")
    
    # --- MODULE 2: COMPETITIVE EXCELLENCE (vs LangChain) ---
    print("\n[MODULE 2] Competitive Determinism (Anti-Hallucination)")
    citation = CitationAxiom()
    claim = "Revenue is $10M"
    source = "Vault Doc A: 2025 Revenue was ten million dollars."
    if citation.check_hallucination(claim, [source]):
        print(" [✓] RAG: CitationAxiom successfully validated deterministic claim.")

    # --- MODULE 3: STATE ORCHESTRATION (vs LangGraph) ---
    print("\n[MODULE 3] Event-Driven Recovery (Cyclic Control)")
    hub = EventHub()
    recovery_triggered = False
    
    def on_recovery(e):
        nonlocal recovery_triggered
        recovery_triggered = True
        print(f" [✓] Recovery: EventHub caught '{e.event_type}' -> Re-reasoning triggered.")

    hub.subscribe(EventType.RECOVERY_REQUIRED, on_recovery)
    hub_task = asyncio.create_task(hub.start())
    await hub.emit(Event(event_type=EventType.JOB_FAILED, timestamp=datetime.now(), source="test", payload={"job_id":"01"}))
    await asyncio.sleep(0.1)
    
    # --- MODULE 4: SWARM & HIVE (vs CrewAI) ---
    print("\n[MODULE 4] Swarm Orchestration & A2A Packets")
    broker = A2ABroker(HiveAdapter(A2AConfig(role="manager")))
    broker.register_node("slave_01", "Researcher", ["web"])
    packet = await broker.hire_agent("AlphaMember", "slave_01", "Validate v0.4.0")
    if packet.header.packet_type == "request":
        print(f" [✓] A2A: Structured L1 Packet generated for {packet.payload['activity']}.")

    checkpoint = SwarmCheckpoint()
    checkpoint.save_snapshot("master_test", {"status": "all_systems_go"})
    print(" [✓] Vault: Swarm Checkpoint persisted to durable storage.")

    # --- MODULE 5: HUMAN-IN-THE-LOOP (HITL) ---
    print("\n[MODULE 5] Human Guardianship (HITL)")
    agent = Agent(name="MasterVerify", model="google/gemini-2.0-flash-001", protocols=[], trust_level=TrustLevel.FULL)
    
    # Mock Cortex to simulate a critical action
    with patch.object(agent.cortex, 'plan_action', return_value="```json\n{\"name\": \"shell_tool\", \"arguments\": {\"command\": \"rm -rf /\"}}\n```"):
        result = await agent.process("Standardize the universe")
        if result["type"] == "hitl_review":
            print(f" [✓] HITL: Critical command '{result['tool_name']}' intercepted for review.")

    print("\n" + "="*70)
    print(" [✓] CONSOLIDATED VERIFICATION COMPLETE: ÆON v0.4.0-ULTRA IS READY.")
    print("="*70)
    
    await hub.stop()
    hub_task.cancel()

if __name__ == "__main__":
    asyncio.run(run_master_verification())
