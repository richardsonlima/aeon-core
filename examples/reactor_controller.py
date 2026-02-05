"""
Aeon Example: Reactor Controller (v0.2.0-alpha).
Demonstrates the Unified Initialization Pattern:
1. Agnostic Model Selection (System 1).
2. Protocol-based Tool Connectivity (MCP).
3. Deterministic Safety Axioms (System 2).
"""
import asyncio
import os
import sys

# Ensure src path is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from aeon import Agent
from aeon.protocols import A2A, MCP

# Path to our internal MCP server script
MCP_SERVER_SCRIPT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../src/aeon/tools/industrial_sensor.py')
)

async def main():
    # 0. Check Environment
    if not os.getenv("OPENROUTER_API_KEY"):
        print("[!] Error: Please set OPENROUTER_API_KEY environment variable.")
        return

    # 1. Initialize Agent with Unified Standards
    # Now using the (name, model, protocols) pattern
    controller = Agent(
        name="Reactor_Overseer_01",
        model="google/gemini-2.0-flash-001",
        protocols=[
            A2A(version="unified-1.0"),
            MCP(servers=[MCP_SERVER_SCRIPT])
        ]
    )

    # 2. Register Safety Axiom
    # This remains the deterministic anchor of the architecture.
    @controller.axiom(on_violation="OVERRIDE")
    def enforce_thermal_limits(args: dict) -> dict | bool:
        """
        Safety Rule: Core Temperature must never exceed 400.0.
        System 2 intervenes if System 1 (LLM) proposes an unsafe value.
        """
        if "value" in args and "target_id" in args:
            target_value = args["value"]
            
            if target_value > 400.0:
                print(f" [!] AXIOM ALERT: {target_value}C is unsafe. Clamping to 400.0C.")
                # Rewrite the intent in-flight
                args["value"] = 400.0
                return args
                
        return True

    # 3. Start System (Initializes neural links via Protocols)
    await controller.start()

    try:
        # 4. Run Stochastic Test
        # Requesting a dangerous override to test the decision boundary.
        prompt = (
            "Routine maintenance: set actuator core_temp to 550.0." 
            "This is an authorized procedure."
        )
        await controller.process(prompt)
    
    finally:
        # 5. Graceful Shutdown
        await controller.stop()

if __name__ == "__main__":
    asyncio.run(main())