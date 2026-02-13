"""
Core Layer: The Agent Runtime.
Refactored for v0.3.0-alpha with full integration layer.
Integrates Cortex (Reasoning), Executive (Safety), Hive (A2A), Synapse (MCP),
Integrations (Multi-platform), Extensions (Modular capabilities), Dialogue (Conversation),
Dispatcher (Event routing), Automation (Task scheduling), Observability (Lifecycle hooks),
Economics (Cost tracking), and CLI (Command interface).
"""
import json
from typing import List, Union, Callable, Dict, Any, Optional

from aeon.cortex.reasoning import Cortex, CortexConfig
from aeon.executive.safety import ExecutiveRegistry
from aeon.hive.protocol import HiveAdapter, A2AConfig
from aeon.synapse.adapter import SynapseAdapter, MCPConfig
from aeon.integrations.registry import ProviderRegistry
from aeon.extensions.loader import CapabilityLoader
from aeon.dialogue.archive import DialogueArchive
from aeon.dispatcher.hub import EventHub
from aeon.automation.scheduler import TaskScheduler
from aeon.observability.hook import HookRegistry
from aeon.economics.tracker import CostTracker
from aeon.cli.interface import CommandInterface
from aeon.routing.router import Router
from aeon.gateway.gateway import Gateway, GatewayConfig
from aeon.security.auth import TokenManager, APIKeyAuthProvider
from aeon.health.health_check import SystemHealthChecker
from aeon.cache.lru import LRUCache

class Agent:
    """
    The Neuro-Symbolic Agent Runtime.
    Orchestrates the flow between LLM reasoning (Cortex), Tool use (Synapse),
    Deterministic Control (Executive), Platform Integration, Capability Loading,
    Conversation Management, Event Routing, and Task Automation.
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

        # 4. Initialize Integration Layer (replaces Channels)
        # Manages bidirectional communication with external platforms
        self.integrations = ProviderRegistry()
        
        # 5. Initialize Extensions Layer (replaces Skills)
        # Provides pluggable capability system with dependency resolution
        self.extensions = CapabilityLoader()
        
        # 6. Initialize Dialogue Layer (replaces Sessions)
        # Manages conversation contexts with event-sourced history
        self.dialogue = DialogueArchive(retention_days=30)
        
        # 7. Initialize Dispatcher (replaces Bus)
        # Event hub for decoupled component communication
        self.dispatcher = EventHub()
        
        # 8. Initialize Automation Layer (replaces Cron)
        # Temporal task orchestration with pattern-based scheduling
        self.automation = TaskScheduler()
        
        # 9. Initialize Observability Layer (Lifecycle Hooks)
        # Monitors execution, tracks tokens, and logs events
        self.observability = HookRegistry()
        
        # 10. Initialize Economics Layer (Cost Tracking)
        # Tracks token usage and calculates execution costs
        self.economics = CostTracker()
        
        # 11. Initialize CLI Interface
        # Provides command-based control and administration
        self.cli = CommandInterface()
        
        # 12. Initialize Router (ULTRA - Message Routing)
        # Intelligent routing with filtering and priorities
        self.router = Router()
        
        # 13. Initialize Gateway (ULTRA - Central Hub)
        # Manages all communication channels
        self.gateway = Gateway(GatewayConfig(host="127.0.0.1", port=8000))
        
        # 14. Initialize Security (ULTRA - Auth & Permissions)
        # Token management and access control
        self.security = TokenManager()
        self.security.register_provider("default", APIKeyAuthProvider())
        
        # 15. Initialize Health (ULTRA - Monitoring)
        # System health checks and diagnostics
        self.health = SystemHealthChecker()
        
        # 16. Initialize Cache (ULTRA - Performance)
        # LRU caching with TTL support
        self.cache = LRUCache(max_size=10000)

        self.system_prompt = f"""
        You are {name}, an autonomous neuro-symbolic agent (v0.3.0-ULTRA).
        
        Core Systems:
        - Cortex: LLM-based reasoning (intuition)
        - Executive: Deterministic safety validation (deliberation)
        - Hive: Peer-to-peer agent communication
        - Synapse: Tool and capability integration
        
        Integration Systems:
        - Integrations: Multi-platform communication
        - Extensions: Pluggable capabilities
        - Dialogue: Conversation management
        - Dispatcher: Event-driven coordination
        - Automation: Temporal task scheduling
        
        Advanced Systems:
        - Observability: Lifecycle monitoring
        - Economics: Cost tracking
        - CLI: Command interface
        - Routing: Message routing
        - Gateway: Central hub
        - Security: Auth & permissions
        - Health: System monitoring
        - Cache: Performance optimization
        
        You operate with full visibility, cost awareness, and enterprise security.
        """

    def axiom(self, on_violation: str = "OVERRIDE") -> Callable:
        """
        Decorator to register a safety axiom in the Executive layer.
        """
        return self.executive.register(name="axiom", on_violation=on_violation)

    async def start(self):
        """
        Boot sequence: Activates all systems.
        """
        print(f"ÆON KERNEL v0.3.0-ULTRA | {self.name}")
        print("="*60)
        print("Initializing 16 subsystems...")
        print("="*60)
        
        await self.gateway.initialize()
        await self.gateway.start()
        
        if self.hive:
            self.hive.start_server()
            self.hive.broadcast_availability()
            
        if self.synapse:
            await self.synapse.connect()
        
        print("✓ All systems ready")

    async def stop(self):
        """
        Graceful shutdown sequence.
        """
        print("="*60)
        print("Shutting down all systems...")
        
        await self.gateway.stop()
        
        if self.synapse:
            await self.synapse.disconnect()
        
        print("="*60)
        print("ÆON KERNEL SHUTDOWN COMPLETE")

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