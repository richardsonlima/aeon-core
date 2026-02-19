
import os
from typing import Any, Dict
from aeon.tools.base import BaseTool

class WorkspaceTool(BaseTool):
    """
    Ultra-Capability: Workspace Awareness.
    Allows the agent to explore its project structure.
    """
    def __init__(self):
        super().__init__(
            name="workspace_discovery",
            description="Explore the current project file structure (list files/folders)."
        )
        self.parameters = {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to explore (default is current directory '.')",
                    "default": "."
                }
            }
        }

    async def execute(self, path: str = ".", **kwargs) -> Any:
        try:
            # Prevent escaping the Git root for safety if possible
            # But here we assume TrustLevel.FULL for personal assistant
            items = os.listdir(path)
            # Filter out hidden files and junk
            filtered = [f for f in items if not f.startswith('.')]
            return {
                "current_path": os.path.abspath(path),
                "contents": filtered[:50] # Limit to 50 items
            }
        except Exception as e:
            return f"Error exploring workspace: {e}"
