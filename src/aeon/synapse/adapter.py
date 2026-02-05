"""
Synapse Layer: Nervous System.
Handles MCP Client connections to local or remote tools.
"""
import asyncio
from contextlib import AsyncExitStack
from typing import List, Dict, Any, Optional

# Official SDK imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class SynapseAdapter:
    """
    Manages the lifecycle of MCP tool connections using the official SDK.
    """
    def __init__(self, server_script_path: str):
        """
        Initialize the adapter with server parameters.
        We use 'uv run' to ensure the sub-process has the correct environment.
        """
        self.server_params = StdioServerParameters(
            command="uv", 
            args=["run", server_script_path], 
        )
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect(self):
        """
        Establishes the stdio connection to the MCP server.
        """
        print(" [+] Synapse: Establishing neural link to MCP tools...")
        
        # Connect to stdio transport
        transport = await self.exit_stack.enter_async_context(
            stdio_client(self.server_params)
        )
        self.read, self.write = transport
        
        # Start the client session
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.read, self.write)
        )
        
        await self.session.initialize()
        
        # Verify connection by listing tools
        tools = await self.session.list_tools()
        tool_names = [t.name for t in tools.tools]
        print(f" [+] Synapse: Connected. Available Tools: {tool_names}")

    async def disconnect(self):
        """
        Cleanly closes the MCP connection and exit stack.
        Critical to avoid asyncio RuntimeErrors on shutdown.
        """
        print(" [-] Synapse: Closing neural link...")
        await self.exit_stack.aclose()

    async def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Converts MCP tools to OpenAI Tool format for the Cortex layer.
        """
        if not self.session:
            return []
            
        result = await self.session.list_tools()
        openai_tools = []
        
        for tool in result.tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            })
        return openai_tools

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Executes a tool call via the MCP session.
        """
        if not self.session:
            raise RuntimeError("Synapse not connected.")
            
        result = await self.session.call_tool(name, arguments)
        return result