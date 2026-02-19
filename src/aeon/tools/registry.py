from typing import Dict, List, Any
from aeon.tools.base import BaseTool

class ToolRegistry:
    """Registry to manage and discover native Æon tools"""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a new tool in the framework"""
        self._tools[tool.name] = tool
        print(f"🛠️ Tool registered: {tool.name}")

    def get_tool(self, name: str) -> BaseTool:
        """Retrieve a tool by name"""
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found in registry")
        return self._tools[name]

    def list_tools(self) -> List[str]:
        """List all registered tool names"""
        return list(self._tools.keys())

    def get_all_definitions(self) -> List[Dict[str, Any]]:
        """Returns list of all tool definitions for LLM context"""
        return [tool.definition for tool in self._tools.values()]

    async def execute_tool(self, name: str, **kwargs) -> Any:
        """Helper to execute a tool by name"""
        tool = self.get_tool(name)
        return await tool.execute(**kwargs)
