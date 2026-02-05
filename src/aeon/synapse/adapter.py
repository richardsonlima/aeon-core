"""
Synapse Layer: Nervous System.
Refactored to support protocol-based configuration (MCPConfig).
Responsible for managing neural links to external tools and sensors.
"""
from typing import List, Dict, Any, Optional
from contextlib import AsyncExitStack
from pydantic import BaseModel

# Official MCP SDK imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPConfig(BaseModel):
    """
    Configuration model for the Model Context Protocol.
    In v0.2.0, it supports local server scripts via stdio.
    """
    servers: List[str]

class SynapseAdapter:
    """
    Adapter for Anthropic's Model Context Protocol (MCP).
    Manages sub-process lifecycles and tool discovery for the Cortex.
    """
    def __init__(self, config: MCPConfig):
        """
        Initialize the adapter with a standard MCP configuration.
        """
        self.config = config
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect(self):
        """
        Establishes neural links to the configured MCP servers.
        Currently handles the primary server in the cluster.
        """
        print(" [+] Synapse: Establishing neural links to MCP servers...")
        
        # In v0.2.0-alpha, we initialize the first server in the config
        # Multi-server multiplexing is scheduled for v0.3.0
        if not self.config.servers:
            print(" [!] Synapse Error: No MCP servers provided in configuration.")
            return

        server_script = self.config.servers[0]
        
        server_params = StdioServerParameters(
            command="uv", 
            args=["run", server_script], 
        )

        try:
            # Enter the stdio communication context
            transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.read, self.write = transport
            
            # Initialize the official MCP Client Session
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.read, self.write)
            )
            
            await self.session.initialize()
            
            # Discovery phase
            tools = await self.session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f" [+] Synapse: Connected. Available Tools: {tool_names}")
            
        except Exception as e:
            print(f" [!] Synapse Connection Error: {e}")
            await self.exit_stack.aclose()

    async def disconnect(self):
        """
        Gracefully closes all neural links and sub-processes.
        """
        print(" [-] Synapse: Closing neural link...")
        await self.exit_stack.aclose()

    async def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Maps MCP capabilities to the Cortex (LLM) tool format.
        """
        if not self.session:
            return []
            
        result = await self.session.list_tools()
        
        # Convert to OpenAI/OpenRouter functional calling format
        return [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in result.tools]

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Executes a deterministic action via the established link.
        """
        if not self.session:
            raise RuntimeError("Synapse: neural link not established.")
            
        return await self.session.call_tool(name, arguments)