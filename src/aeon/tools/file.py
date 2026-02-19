import os
import shutil
import glob
from typing import Any
from aeon.tools.base import BaseTool

class FileTool(BaseTool):
    """System tool for filesystem operations"""
    
    def __init__(self):
        super().__init__(
            name="file_system",
            description="Perform filesystem operations like reading, writing, and listing files."
        )
        self.parameters = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["read", "write", "list", "search", "delete", "mkdir"],
                    "description": "The action to perform"
                },
                "path": {
                    "type": "string",
                    "description": "Target file or directory path"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write (for 'write' action)"
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern for 'search' action"
                }
            },
            "required": ["action", "path"]
        }

    async def execute(self, **kwargs) -> Any:
        action = kwargs.get("action")
        path = os.path.abspath(kwargs.get("path"))
        
        if action == "read":
            if not os.path.exists(path):
                return f"Error: File {path} does not exist"
            with open(path, "r") as f:
                return f.read()
                
        elif action == "write":
            content = kwargs.get("content", "")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            return f"Successfully wrote to {path}"
            
        elif action == "list":
            if not os.path.exists(path):
                return f"Error: Directory {path} does not exist"
            return os.listdir(path)
            
        elif action == "search":
            pattern = kwargs.get("pattern", "*")
            search_path = os.path.join(path, pattern)
            return glob.glob(search_path, recursive=True)
            
        elif action == "delete":
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            return f"Deleted {path}"
            
        elif action == "mkdir":
            os.makedirs(path, exist_ok=True)
            return f"Created directory {path}"
            
        return f"Unknown action: {action}"
