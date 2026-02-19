import asyncio
import os
import sys
from typing import List

# Add src to path
sys.path.append(os.path.abspath("src"))

from aeon.core.agent import Agent
from aeon.security.trust import TrustLevel
from aeon.synapse.adapter import MCPConfig
from aeon.tools.macos import MacOSTool

async def run_evidence_test():
    print("\n" + "="*60)
    print(" 🧪 AEON INTELLIGENCE V2 EVIDENCE TEST")
    print("="*60)

    # Initialize Agent with local Ollama model
    agent = Agent(
        name="Tester",
        model="ollama/phi3.5",
        protocols=[MCPConfig(servers=[])], # No MCP servers needed for this test scenario
        trust_level=TrustLevel.FULL
    )
    
    # Register macOS Tool for evidence
    agent.tools.register(MacOSTool())

    print("\n[SCENARIO 1] Reasoning Isolation & Thinking Tags")
    print("-" * 40)
    # This prompt is designed to make the model think and act
    response = await agent.process("Lembre-me de comprar melão amanhã")
    
    # Evidence: Check if ReasoningStepEvent was created
    recent_events = agent.memory.get_recent(limit=5)
    thoughts = [e.thought for e in recent_events if e.type == "reasoning_step"]
    
    if thoughts:
        print(f" [✓] Evidence Found: Found internal thought block.")
        print(f"     Thought Sample: {thoughts[0][:100]}...")
    else:
        print(" [!] No internal thoughts found in memory.")

    print("\n[SCENARIO 2] Multi-turn Memory (SQLite Context)")
    print("-" * 40)
    # Ask a follow-up that depends on the previous turn
    response_2 = await agent.process("O que eu acabei de pedir para você lembrar?")
    
    if "melão" in str(response_2).lower():
        print(f" [✓] Evidence Found: Agent remembered 'melão' from history.")
        print(f"     Response: {response_2}")
    else:
        print(f" [!] Agent failed to remember. Response: {response_2}")

    print("\n[SCENARIO 3] Reasoning Axiom Enforcement")
    print("-" * 40)
    # Mock a scenario where reasoning is missing for a high-stakes call
    # We'll use a manual validation against the axiom
    result = agent.reasoning_axiom.validate_reasoning("macos_system", "")
    if result is False:
        print(" [✓] Evidence Found: ReasoningAxiom blocked tool call without thought.")
    else:
        print(" [!] ReasoningAxiom failed to block empty thought.")

    print("\n" + "="*60)
    print(" ✅ TEST SEQUENCE COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_evidence_test())
