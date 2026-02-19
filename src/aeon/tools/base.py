from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ToolDefinition(BaseModel):
    """Schema for tool definition used by LLMs (OpenAI format)"""
    name: str
    description: str
    parameters: Dict[str, Any]

class BaseTool(ABC):
    """Base abstract class for all native Æon tools"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }

    @property
    def definition(self) -> Dict[str, Any]:
        """Returns the dictionary representation for LLM function calling"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Main execution logic for the tool"""
        pass
