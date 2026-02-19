import sys
import os
import asyncio
from datetime import datetime

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from aeon.core.packet import Packet
from aeon.executive.citation import CitationAxiom
from aeon.dispatcher.hub import EventHub
from aeon.dispatcher.event import Event, EventType
from aeon.dispatcher.recovery import RecoveryHandler

async def verify_competitive_features():
    print(" [~] Initiating Æon vs Frameworks (LangChain/CrewAI) Verification...")
    
    # 1. Verify L1 Packet (Structured Communication)
    print("\n [1] Testing L1 Packet (A2A Protocol):")
    packet = Packet.create_request(
        sender="AgentA", 
        receiver="AgentB", 
        activity="data_analysis", 
        params={"dataset": "financial_v1"}
    )
    json_data = packet.serialize()
    deserialized = Packet.deserialize(json_data)
    
    if deserialized.header.sender_id == "AgentA" and deserialized.payload["activity"] == "data_analysis":
        print("     [OK] Packet serialization/deserialization successful and structured.")
    else:
        print("     [FAIL] Packet logic corrupted.")

    # 2. Verify L3 CitationAxiom (Deterministic RAG)
    print("\n [2] Testing L3 CitationAxiom (Anti-Hallucination):")
    axiom = CitationAxiom()
    response = "Based on [1], the revenue is $5M."
    context = "Document [1]: 2024 Revenue was $5 million dollars."
    
    is_valid = axiom.validate_response(response, context)
    fact_check = axiom.check_hallucination("$5M", [context])
    
    if is_valid and fact_check:
        print("     [OK] Citation validated and claim verified against Vault.")
    else:
        print("     [FAIL] Citation validation failed.")

    # 3. Verify L4 Recovery Logic (State Orchestration)
    print("\n [3] Testing L4 Event-Driven Recovery:")
    hub = EventHub()
    handler = RecoveryHandler(hub)
    
    # Track if recovery event was emitted
    recovery_emitted = False
    def on_recovery(event):
        nonlocal recovery_emitted
        recovery_emitted = True
        print(f"     [>] EventHub: Caught '{event.event_type}' for Job '{event.payload['job_id']}'")

    hub.subscribe(EventType.RECOVERY_REQUIRED, on_recovery)
    
    # Start the hub in background
    hub_task = asyncio.create_task(hub.start())
    
    # Emit a failure
    fail_event = Event(
        event_type=EventType.JOB_FAILED,
        timestamp=datetime.now(),
        source="BrowserTool",
        payload={"job_id": "scrape_01", "error": "Timeout"}
    )
    await hub.emit(fail_event)
    
    # Wait for processing
    await asyncio.sleep(0.1)
    
    if recovery_emitted:
        print("     [OK] Dispatcher successfully converted failure into a Recovery lifecycle.")
    else:
        print("     [FAIL] Recovery event was not emitted.")
    
    await hub.stop()
    hub_task.cancel()

    print("\n [✓] Competitive Excellence Verification Complete!")

if __name__ == "__main__":
    asyncio.run(verify_competitive_features())
