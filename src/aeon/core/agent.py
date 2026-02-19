"""
Core Layer: The Agent Runtime.
Refactored for v0.3.0-alpha with full integration layer.
Integrates Cortex (Reasoning), Executive (Safety), Hive (A2A), Synapse (MCP),
Integrations (Multi-platform), Extensions (Modular capabilities), Dialogue (Conversation),
Dispatcher (Event routing), Automation (Task scheduling), Observability (Lifecycle hooks),
Economics (Cost tracking), and CLI (Command interface).
"""
import json
import re
from typing import List, Union, Callable, Dict, Any, Optional

from aeon.cortex.reasoning import Cortex, CortexConfig
from aeon.executive.safety import ExecutiveRegistry
from aeon.hive.protocol import HiveAdapter, A2AConfig
from aeon.synapse.adapter import SynapseAdapter, MCPConfig
from aeon.integrations.registry import ProviderRegistry
from aeon.extensions.loader import CapabilityLoader
from aeon.dialogue.archive import DialogueArchive
from aeon.dispatcher.hub import EventHub
from aeon.dispatcher.webhook import WebhookListener
from aeon.automation.scheduler import TaskScheduler
from aeon.observability.hook import HookRegistry
from aeon.economics.tracker import CostTracker
from aeon.cli.interface import CommandInterface
from aeon.routing.router import Router
from aeon.gateway.gateway import Gateway, GatewayConfig
from aeon.security.auth import TokenManager, APIKeyAuthProvider
from aeon.health.health_check import SystemHealthChecker
from aeon.cache.lru import LRUCache
from aeon.tools.registry import ToolRegistry
from aeon.tools.file import FileTool
from aeon.tools.shell import ShellTool
from aeon.tools.browser import BrowserTool
from aeon.tools.workspace import WorkspaceTool
from aeon.runtime.loop import AgentLoop
from aeon.memory.store import EventStore
from aeon.memory.durable import DurableStore
from aeon.memory.events import (
    AgentStartEvent, UserMessageEvent, ReasoningStepEvent, ToolExecutionEvent, ToolResultEvent
)
from aeon.security.trust import TrustLevel, SecurityContext
from aeon.executive.hitl import HITLAxiom
from aeon.axioms.reasoning_axiom import ReasoningAxiom


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
        protocols: List[Union[A2AConfig, MCPConfig]],
        trust_level: TrustLevel = TrustLevel.FULL
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
        
        # 13.5 Initialize Webhook Listener (Phase 3)
        # Listens for external POST events
        self.webhooks = WebhookListener(port=8001, event_hub=self.dispatcher)
        
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

        # 17. Initialize Native Tool Registry
        # Built-in capabilities that run directly on the system
        self.tools = ToolRegistry()
        self.tools.register(FileTool())
        self.tools.register(ShellTool())
        self.tools.register(BrowserTool(headless=True))
        self.tools.register(WorkspaceTool())

        # 18. Initialize Agent Loop (Consciousness)
        # Manages continuous reasoning-action cycles
        self.loop = AgentLoop(self)

        # 19. Initialize Memory (Event Sourcing)
        # Immutable history of all agent actions
        self.memory = EventStore()
        self.durable = DurableStore()
        self.memory.append(AgentStartEvent(agent_name=name, model=model))

        # 20. Initialize Security Context
        # Enforces trust boundaries for tool execution
        self.security_context = SecurityContext(trust_level)
        
        # 21. Initialize HITL (Human-in-the-loop) Axiom
        self.hitl = HITLAxiom()
        
        # 22. Initialize Reasoning Axiom (Intelligence v2)
        self.reasoning_axiom = ReasoningAxiom()

        self.system_prompt = f"""
        # Æon Framework
        You are Æon. Use tools to solve the request.
        1. REASONING: Explain in <think>...</think>
        2. ACTION: Provide EXACTLY ONE tool call in ```json format.
        
        Rules:
        - NEVER suggest tools, execute them.
        - NEVER explain instructions outside tags.
        - ONLY use tools in the catalog.
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
        
        # Phase 3: Start Automation and Webhooks
        await self.automation.start()
        await self.webhooks.start()
            
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
            
        # Phase 3: Stop Automation and Webhooks
        await self.automation.stop()
        await self.webhooks.stop()
        
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
        
        # Record user input
        self.memory.append(UserMessageEvent(content=user_input))

        # 1. Discovery phase (Get all available tools)
        combined_tools = []
        
        # Add native tools
        combined_tools.extend(self.tools.get_all_definitions())
        
        # Add Synapse/MCP tools if available
        if self.synapse:
            try:
                mcp_tools = await self.synapse.get_tool_definitions()
                if mcp_tools:
                    combined_tools.extend(mcp_tools)
            except Exception as e:
                print(f" [!] Error fetching MCP tools: {e}")

        # 2. Reasoning phase (Cortex/LLM)
        # Detailed Tool Catalog
        tool_catalog = "\n## Available Tools\n"
        for t in combined_tools:
            func = t.get('function', {})
            name = func.get('name')
            if name:
                tool_catalog += f"### {name}\nDescription: {func.get('description', '')}\n"
                params = func.get('parameters', {}).get('properties', {})
                if params:
                    tool_catalog += f"  - Parameters: {list(params.keys())}\n"

        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Language Anchor
        lang_hint = "Português" if any(x in user_input.lower() for x in ["o", "a", "é", "que", "como", "fazer", "crie", "lista"]) else "English"
        
        dynamic_system_prompt = self.system_prompt + "\n" + tool_catalog
        dynamic_system_prompt += f"\n## KERNEL STATUS\nClock: {now}\nLang: {lang_hint}\n"
        
        # Inject Durable Memory
        dynamic_system_prompt += self.durable.get_context()
        
        dynamic_system_prompt += f"\n\nCOMMAND: {user_input}\nINSTRUCTION: Execute the COMMAND above using tools. Be clinical."

        # Convert memory events to valid LLM message history
        history_messages = []
        recent_events = self.memory.get_recent(limit=3) 
        
        for event in recent_events:
            event_type = getattr(event, 'type', '')
            if event_type == "user_message":
                history_messages.append({"role": "user", "content": getattr(event, 'content', "")})
            elif event_type == "reasoning_step":
                thought = getattr(event, 'thought', '')
                # Sterilize history: if it looks like a loop, purge its thought
                if thought and "search" not in thought.lower() and "time" not in thought.lower():
                    history_messages.append({"role": "assistant", "content": f"<think>{thought}</think>"})
            elif event_type == "tool_result":
                output = str(getattr(event, 'output', ''))
                # Sterilize search results to break loops
                if "duckduckgo" not in output.lower() and "timeanddate" not in output.lower():
                    history_messages.append({"role": "user", "content": f"Result: {output[:500]}"})

        llm_decision = self.cortex.plan_action(dynamic_system_prompt, history_messages, combined_tools)


        if not hasattr(llm_decision, 'function'):
            # Hyper-Robust Extraction for local models (Mistral, Llama, etc.)
            content = str(llm_decision).strip()
            
            # --- Intelligence Axiom v2: Reasoning Isolation ---
            thought_match = re.search(r"<think>([\s\S]*?)<\/think>", content)
            
            if thought_match:
                thought = thought_match.group(1).strip()
            else:
                # Heuristic for local models: use pre-JSON text as thought if tags are missing
                json_match = re.search(r"(\{[\s\S]*\})", content)
                if json_match:
                    thought = content[:json_match.start()].strip()
                    # If still empty or trivial, check post-JSON
                    if len(thought) < 5:
                        post_thought = content[json_match.end():].strip()
                        if len(post_thought) > len(thought):
                            thought = post_thought
                else:
                    thought = content # It's likely just a text response

            # Clean content for tool extraction (remove the think block if it exists)
            extraction_content = re.sub(r"<think>[\s\S]*?<\/think>", "", content).strip()
            
            if thought:
                print(f" [i] Cortex Thought: {thought}")
                self.memory.append(ReasoningStepEvent(thought=thought))
            # --------------------------------------------------

            proposed_tool = None

            # 1. Try to find ANY JSON-like block (greedy to catch nested stuff)

            
            # Use Brace-Balancing extraction for nested JSON support
            def extract_json_blocks(text):
                blocks = []
                stack = []
                start = -1
                for i, char in enumerate(text):
                    if char == '{':
                        if not stack:
                            start = i
                        stack.append('{')
                    elif char == '}':
                        if stack:
                            stack.pop()
                            if not stack:
                                blocks.append(text[start:i+1])
                return blocks
                
            matches = extract_json_blocks(extraction_content)
        
        for match in matches:
            try:
                # Cleanup common non-standard wrappers
                clean_match = match
                
                # If it's a list, take the first element (common in some formats)
                parsed = json.loads(clean_match)
                if isinstance(parsed, list) and len(parsed) > 0:
                    parsed = parsed[0]
                
                # --- KEY MAPPING (Hyper-Robustness for Phi-3.5) ---
                # Map 'tool' or 'action' (if it points to a tool) to 'name'
                known_tool_names = [t.get('function', {}).get('name') for t in combined_tools]
                
                # Identify tool name from common keys
                suggested_name = parsed.get("name", parsed.get("tool", parsed.get("action")))
                if suggested_name in known_tool_names and "name" not in parsed:
                    parsed["name"] = suggested_name
                
                # Map 'parameters' or 'params' to 'arguments'
                if "parameters" in parsed and "arguments" not in parsed and "args" not in parsed:
                    parsed["arguments"] = parsed["parameters"]
                if "params" in parsed and "arguments" not in parsed and "args" not in parsed:
                    parsed["arguments"] = parsed["params"]

                # --- VALIDATION: Only accept known tools ---
                known_tool_names = [t.get('function', {}).get('name') for t in combined_tools]
                target_name = parsed.get("name", parsed.get("tool"))

                if target_name and any(target_name.lower() == k.lower() for k in known_tool_names):
                    # Normalized name
                    tool_name = next(k for k in known_tool_names if k.lower() == target_name.lower())
                    # Arguments extraction
                    if "arguments" in parsed:
                        tool_args = parsed["arguments"]
                    elif "args" in parsed:
                        tool_args = parsed["args"]
                    else:
                        tool_args = {k: v for k, v in parsed.items() if k not in ["name", "tool", "params", "parameters"]}
                    
                    proposed_tool = {"name": tool_name, "args": tool_args}
                    print(f" [i] Cortex Intent (Validated Extract): {tool_name}")
                    break
                
                # Heuristic mapping removed in v11 for stability. 
                # Meta-key filtering in the primary block now handles flat objects correctly.
                pass
            except:
                # 2. Try to fix "JS-style" objects (unquoted keys)
                try:
                    # Replace unquoted keys (e.g., action: -> "action":)
                    fixed_match = re.sub(r'(\w+)\s*:', r'"\1":', match)
                    # Replace single quotes with double quotes (carefully)
                    fixed_match = fixed_match.replace("'", '"')
                    parsed = json.loads(fixed_match)
                    if "action" in parsed or "name" in parsed:
                        # If it's just the args (Mistral style), we attempt to map it
                        if "action" in parsed:
                            # Heuristic: if it contains 'action', it's likely macos_system
                            proposed_tool = {"name": "macos_system", "args": parsed}
                        else:
                            proposed_tool = {"name": parsed.get("name"), "args": parsed.get("arguments", {})}
                        
                        print(f" [i] Cortex Intent (Repaired JS-Object): {proposed_tool['name']}")
                        break
                except:
                    continue

        # 3. Last resort: Pattern matching for pseudo-function calls
        if not proposed_tool:
            # Pattern A: tool_name({ ... }) - Object style
            func_obj_match = re.search(r"(\w+)\s*\(\s*(\{[\s\S]*?\})\s*\)", content)
            if func_obj_match:
                tool_name = func_obj_match.group(1)
                inner_obj = func_obj_match.group(2)
                try:
                    # Clean the inner object
                    fixed_obj = re.sub(r'(\w+)\s*:', r'"\1":', inner_obj).replace("'", '"')
                    tool_args = json.loads(fixed_obj)
                    proposed_tool = {"name": tool_name, "args": tool_args}
                    print(f" [i] Cortex Intent (Function-Object-Regex): {tool_name}")
                except:
                    pass
            
            # Pattern B: tool_name(key="val", key2="val2") - Keyword style
            if not proposed_tool:
                func_kw_match = re.search(r"(\w+)\s*\(([\s\S]*?)\)", content)
                if func_kw_match:
                    tool_name = func_kw_match.group(1)
                    args_str = func_kw_match.group(2)
                    # Extract key="value" or key='value' pairs
                    arg_pairs = re.findall(r'(\w+)\s*=\s*["\'](.*?)["\']', args_str)
                    if arg_pairs:
                        tool_args = {k: v for k, v in arg_pairs}
                        proposed_tool = {"name": tool_name, "args": tool_args}
                        print(f" [i] Cortex Intent (Keyword-Args-Regex): {tool_name}")

        if proposed_tool:
            # Governance phase (Executive/Axioms)
            tool_name = proposed_tool["name"]
            tool_args = proposed_tool["args"]
        elif hasattr(llm_decision, 'function'):
            # Traditional tool call object (OpenAI spec)
            tool_name = llm_decision.function.name
            try:
                tool_args = json.loads(llm_decision.function.arguments)
            except json.JSONDecodeError:
                print(" [!] Cortex Error: Generated invalid JSON arguments.")
                return None
            proposed_tool = {"name": tool_name, "args": tool_args}
            print(f" [i] Cortex Intent: Call {tool_name}")
        else:
            print(f" [i] Cortex Response (Text): {llm_decision}")
            return {"type": "text", "content": llm_decision}

        # 3. Governance phase (Executive/Axioms)
        # Deterministic override happens here before any external impact.
        tool_name = proposed_tool["name"]
        tool_args = proposed_tool["args"]
        
        # Record reasoning step
        self.memory.append(ReasoningStepEvent(
            thought=str(llm_decision) if hasattr(llm_decision, 'function') else "Tool Call",
            tool_call=proposed_tool
        ))

        # Check Security Context
        if not self.security_context.can_execute(tool_name):
            msg = f"Security Violation: Tool '{tool_name}' is not allowed at trust level {self.security_context.level.value}"
            print(f" [!] BLOCKED by Security: {msg}")
            return {"type": "error", "content": msg}

        # Check HITL Requirements
        if self.hitl.requires_review(tool_name, tool_args):
            print(f" [!] HITL: Review required for tool '{tool_name}'.")
            return {
                "type": "hitl_review", 
                "tool_name": tool_name, 
                "args": tool_args,
                "content": f"Manual approval required for {tool_name}"
            }

        # Check Reasoning Axiom (Intelligence v2)
        # macos_system is always allowed for Personal Assistant UX
        if tool_name != "macos_system":
            if not self.reasoning_axiom.validate_reasoning(tool_name, thought if 'thought' in locals() else ""):
                msg = f"Reasoning Violation: Tool '{tool_name}' requires internal explanation but provided empty thoughts."
                print(f" [!] BLOCKED by Reasoning Axiom: {msg}")
                return {"type": "error", "content": msg}

        try:
            safe_args = self.executive.validate_output(tool_args)
        except Exception as e:
            print(f" [!] BLOCKED by Executive: {e}")
            return {"type": "error", "content": str(e)}


        # 4. Action phase (Execution - Native or Synapse)
        try:
            # Check if it's a native tool
            if tool_name in self.tools.list_tools():
                self.memory.append(ToolExecutionEvent(
                    tool_name=tool_name, arguments=safe_args, status="started"
                ))
                
                result = await self.tools.execute_tool(tool_name, **safe_args)
                result_str = str(result)
                
                self.memory.append(ToolResultEvent(
                    tool_name=tool_name, output=result_str
                ))
                
                print(f" [<] Native Tool Output: {result_str}")
                return {"type": "action_result", "content": result_str}
                
            # Otherwise use Synapse/MCP
            if self.synapse:
                # Note: Synapse doesn't have detailed event tracking yet
                result = await self.synapse.execute_tool(tool_name, safe_args)
                output_text = result.content[0].text if result.content else "No output"
                print(f" [<] Synapse Tool Output: {output_text}")
                return {"type": "action_result", "content": output_text}
            
            print(f" [!] Tool '{tool_name}' not found locally or via Synapse.")
            return None
            
        except Exception as e:
            print(f" [!] Execution Error ({tool_name}): {e}")
            self.memory.append(ToolResultEvent(
                tool_name=tool_name, output="", error=str(e)
            ))
            return None

    async def run(self, goal: str, max_steps: int = 10):
        """Shortcut to run the agent in autonomous loop mode"""
        return await self.loop.run(goal, max_steps)