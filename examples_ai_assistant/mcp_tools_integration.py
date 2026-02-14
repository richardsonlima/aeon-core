"""
MCP Tools Integration - Generic Setup

This example shows how to integrate any MCP server with your agent.

Available MCP Servers from mcpserverhub.com:
  - Brave Search (web search)
  - Google Maps (location & directions)
  - Puppeteer (web scraping)
  - SQLite (database queries)
  - YouTube Data (video transcripts)
  - Time (timezone conversion)
  - Sequential Thinking (structured reasoning)

Setup:
    pip install mcp
    python mcp_tools_integration.py
"""

import asyncio
import json
from aeon import Agent
from aeon.synapse.mcp import MCPClient


class MCPToolIntegration:
    """Generic MCP server integration"""
    
    def __init__(self, agent: Agent, mcp_servers: list[str]):
        self.agent = agent
        self.mcp_servers = mcp_servers
        self.tools = {}

    async def initialize(self):
        """Initialize MCP clients for each server"""
        for server in self.mcp_servers:
            print(f"  Initializing {server}...", end="", flush=True)
            try:
                # Create MCP client for this server
                # In real implementation, this would connect to the server
                self.tools[server] = {
                    "status": "connected",
                    "tools": self._get_mock_tools(server)
                }
                print(" ✓")
            except Exception as e:
                print(f" ✗ ({e})")

    def _get_mock_tools(self, server: str) -> list:
        """Get available tools for a server (mock data)"""
        tools_map = {
            "brave_search": [
                {"name": "search", "description": "Search the web"},
                {"name": "news", "description": "Search news"}
            ],
            "google_maps": [
                {"name": "get_location", "description": "Get coordinates"},
                {"name": "get_directions", "description": "Get driving directions"},
                {"name": "nearby_places", "description": "Find nearby places"}
            ],
            "puppeteer": [
                {"name": "screenshot", "description": "Take page screenshot"},
                {"name": "scrape", "description": "Extract page content"},
                {"name": "click", "description": "Interact with page"}
            ],
            "sqlite": [
                {"name": "query", "description": "Execute SQL query"},
                {"name": "insert", "description": "Insert data"},
                {"name": "update", "description": "Update data"}
            ],
            "youtube": [
                {"name": "get_transcript", "description": "Get video transcript"},
                {"name": "get_comments", "description": "Get video comments"}
            ]
        }
        return tools_map.get(server, [])

    async def call_tool(self, server: str, tool: str, params: dict) -> str:
        """Call a tool on an MCP server"""
        if server not in self.tools:
            return f"Server '{server}' not initialized"
        
        available_tools = [t["name"] for t in self.tools[server]["tools"]]
        if tool not in available_tools:
            return f"Tool '{tool}' not found on server '{server}'"
        
        # In real implementation, this would call the actual MCP server
        print(f"  Calling {server}.{tool}({params})...")
        
        # Simulate tool response
        mock_responses = {
            "search": "Found 5 results about your query...",
            "get_location": "Found: 40.7128°N, 74.0060°W",
            "get_directions": "Drive 5.2 miles (12 minutes) via Main St",
            "nearby_places": "Coffee shops: Brew Haven (0.1 mi), Java Express (0.3 mi)",
            "query": "Query executed, returned 42 rows",
            "get_transcript": "Transcript retrieved (2000 words)",
            "screenshot": "Screenshot saved to /tmp/screenshot.png"
        }
        
        return mock_responses.get(tool, "Tool execution result")


async def main():
    print("=" * 60)
    print("Æon Framework - MCP Tools Integration")
    print("=" * 60)

    # Initialize agent
    agent = Agent(
        name="MCPAgent",
        model_provider="ollama",
        model_name="mistral"
    )

    # Initialize MCP tools
    print("\nInitializing MCP Servers:")
    mcp_servers = [
        "brave_search",
        "google_maps",
        "puppeteer",
        "sqlite",
        "youtube"
    ]

    mcp_integration = MCPToolIntegration(agent, mcp_servers)
    await mcp_integration.initialize()

    print("\nAvailable Tools:")
    for server, data in mcp_integration.tools.items():
        tools = data["tools"]
        tool_names = ", ".join([t["name"] for t in tools])
        print(f"  {server}: {tool_names}")

    # Example usage
    print("\n" + "=" * 60)
    print("Example: Using MCP Tools")
    print("=" * 60)

    # Use Brave Search
    print("\n[1] Searching with Brave Search:")
    result = await mcp_integration.call_tool(
        "brave_search",
        "search",
        {"query": "Æon Framework agent"}
    )
    print(f"  Result: {result}")

    # Use Google Maps
    print("\n[2] Getting directions with Google Maps:")
    result = await mcp_integration.call_tool(
        "google_maps",
        "get_directions",
        {"from": "New York", "to": "Boston"}
    )
    print(f"  Result: {result}")

    # Use YouTube
    print("\n[3] Getting transcript with YouTube:")
    result = await mcp_integration.call_tool(
        "youtube",
        "get_transcript",
        {"video_id": "dQw4w9WgXcQ"}
    )
    print(f"  Result: {result}")

    # Use SQLite
    print("\n[4] Querying database with SQLite:")
    result = await mcp_integration.call_tool(
        "sqlite",
        "query",
        {"sql": "SELECT * FROM users LIMIT 10"}
    )
    print(f"  Result: {result}")

    # AI-powered tool selection
    print("\n" + "=" * 60)
    print("AI-Powered Tool Selection")
    print("=" * 60)

    prompt = "Find me a good coffee shop near New York and search for their reviews"
    print(f"\nUser: {prompt}")
    print("\nAgent thinking about which tools to use...")
    
    response = await agent.cortex.reason(
        prompt=f"Given these tools available: {', '.join(mcp_servers)}, "
               f"which would be best for: {prompt}"
    )
    print(f"\nAgent recommendation: {response}")


if __name__ == "__main__":
    asyncio.run(main())
