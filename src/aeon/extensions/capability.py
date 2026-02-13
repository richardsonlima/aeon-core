"""
Capability: Extensible agent capability abstraction.
Enables modular feature injection into the agent runtime.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class CapabilityMetadata(BaseModel):
    """Metadata describing a capability."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    dependencies: list[str] = []
    tags: list[str] = []


class Capability(ABC):
    """
    Abstract capability for agent extensions.
    Capabilities are modular, self-contained features that can be dynamically loaded.
    """

    metadata: CapabilityMetadata

    @abstractmethod
    async def activate(self) -> None:
        """Initialize and activate the capability."""
        pass

    @abstractmethod
    async def deactivate(self) -> None:
        """Gracefully deactivate the capability."""
        pass

    @abstractmethod
    async def invoke(self, **kwargs: Any) -> Any:
        """Execute the capability with given parameters."""
        pass

    async def health_check(self) -> Dict[str, Any]:
        """
        Verify capability status and dependencies.
        Returns status dictionary with health information.
        """
        return {"status": "healthy", "name": self.metadata.name}
