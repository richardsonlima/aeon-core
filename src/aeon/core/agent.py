"""
Core Layer: The Agent Runtime.
Refactored for v0.2.0-alpha to support unified protocol initialization.
Integrates Cortex (Reasoning), Executive (Safety), Hive (A2A), and Synapse (MCP).
"""
import json
from typing import List, Union, Callable, Dict, Any, Optional

from aeon.cortex.reasoning import Cortex, CortexConfig
from aeon.executive.safety import ExecutiveRegistry
from aeon.hive.protocol import HiveAdapter, A2AConfig
from aeon.synapse.adapter import SynapseAdapter, MCPConfig

class Agent:
    """
    The Neuro-Symbolic Agent Runtime.
    Orchestrates the flow between LLM reasoning (Cortex), Tool use (Synapse),
    and Deterministic Control (Executive).
    """
    def __init__(
        self, 
        name: str, 
        model: str, 
        protocols: List[Union[A2AConfig, MCPConfig]]
    ):
        """
        Initializes the agent with a name, a specific LLM model, and 
        a list of supported communication and capability protocols.
        """
        self.name = name
        
        # 1. Initialize Cortex with the selected model (System 1)
        self.cortex = Cortex(CortexConfig(model=model))
        
        # 2. Initialize Executive Registry for safety axioms (System 2)
        self.executive = ExecutiveRegistry()
        
        # 3. Initialize Adapters based on protocols
        self.hive: Optional[HiveAdapter] = None
        self.synapse: Optional[SynapseAdapter] = None
        
        for protocol in protocols:
            if isinstance(protocol, A2AConfig):
                self.hive = HiveAdapter(protocol)
            elif isinstance(protocol, MCPConfig):
                self.synapse = SynapseAdapter(protocol)

        self.system_prompt = f"""
        You are {name}, an industrial safety controller.
        You have access to hardware sensors and actuators via tools.
        Fulfill user requests while strictly adhering to safety constraints.
        """

    def axiom(self, on_violation: str = "OVERRIDE") -> Callable:
        """
        Decorator to register a safety axiom in the Executive layer.
        """
        return self.executive.register(name="axiom", on_violation=on_violation)

    async def start(self):
        """
        Boot sequence: Activates Hive (A2A) and Synapse (MCP) neural links.
        """
        print(f"AEON KERNEL v0.2.0-alpha | {self.name}")
        print("-" * 40)
        
        if self.hive:
            self.hive.start_server()
            self.hive.broadcast_availability()
            
        if self.synapse:
            await self.synapse.connect()

    async def stop(self):
        """
        Graceful shutdown sequence to cleanly close neural links.
        """
        if self.synapse:
            await self.synapse.disconnect()
        print("-" * 40)
        print("AEON KERNEL SHUTDOWN")

    async def process(self, user_input: str) -> Optional[Dict[str, Any]]:
        """
        The Neuro-Symbolic Loop:
        1. Discovery: Fetch available tools from Synapse.
        2. Reasoning: Cortex decides the best action.
        3. Governance: Executive validates and potentially overrides the action.
        4. Action: Synapse executes the safe command.
        """
        print(f"\n [>] User Input: {user_input}")

        # 1. Discovery phase (Synapse/MCP)
        if not self.synapse:
            print(" [!] Error: No Synapse/MCP protocol configured.")
            return None

        try:
            tools = await self.synapse.get_tool_definitions()
        except Exception as e:
            print(f" [!] Error fetching tools: {e}")
            return None

        # 2. Reasoning phase (Cortex/LLM)
        llm_decision = self.cortex.plan_action(self.system_prompt, user_input, tools)

        if not hasattr(llm_decision, 'function'):
            print(f" [i] Cortex Response: {llm_decision}")
            return {"type": "text", "content": llm_decision}

        # Parse proposed tool and arguments
        tool_name = llm_decision.function.name
        try:
            tool_args = json.loads(llm_decision.function.arguments)
        except json.JSONDecodeError:
            print(" [!] Cortex Error: Generated invalid JSON arguments.")
            return None
        
        print(f" [i] Cortex Intent: Call {tool_name} with {tool_args}")

        # 3. Governance phase (Executive/Axioms)
        # Deterministic override happens here before any external impact.
        try:
            safe_args = self.executive.validate_output(tool_args)
        except Exception as e:
            print(f" [!] BLOCKED by Executive: {e}")
            return {"type": "error", "content": str(e)}

        # 4. Action phase (Synapse/Execution)
        try:
            result = await self.synapse.execute_tool(tool_name, safe_args)
            output_text = result.content[0].text if result.content else "No output"
            print(f" [<] Tool Output: {output_text}")
            return {"type": "action_result", "content": output_text}
        except Exception as e:
            print(f" [!] Synapse Execution Error: {e}")
            return None