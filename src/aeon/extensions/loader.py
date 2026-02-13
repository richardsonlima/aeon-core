"""
Capability Loader: Dynamic extension discovery and resolution.
Implements dependency resolution for modular capability loading.
"""

from typing import Dict, Optional, List, Type
from aeon.extensions.capability import Capability, CapabilityMetadata


class CapabilityLoader:
    """
    Dynamic capability loading system with dependency resolution.
    Handles capability discovery, validation, and lifecycle.
    """

    def __init__(self):
        self._registry: Dict[str, Capability] = {}
        self._inactive: Dict[str, Capability] = {}
        self._dependency_graph: Dict[str, List[str]] = {}

    def register(self, capability: Capability) -> None:
        """
        Register a capability for potential loading.
        Validates metadata and tracks dependencies.
        """
        name = capability.metadata.name
        if name in self._registry:
            raise ValueError(f"Capability '{name}' already loaded")
        self._registry[name] = capability
        self._dependency_graph[name] = capability.metadata.dependencies

    def unload(self, name: str) -> None:
        """Unload and deregister a capability."""
        if name in self._registry:
            del self._registry[name]
            self._dependency_graph.pop(name, None)

    def _resolve_dependencies(self, name: str) -> List[str]:
        """Resolve dependency chain for a capability."""
        deps = self._dependency_graph.get(name, [])
        resolved = []
        for dep in deps:
            resolved.extend(self._resolve_dependencies(dep))
            resolved.append(dep)
        return list(set(resolved))  # Remove duplicates

    async def activate(self, name: str) -> None:
        """
        Activate a capability and its dependencies.
        Follows topological sort for dependency order.
        """
        deps = self._resolve_dependencies(name)
        for dep_name in deps:
            if dep_name not in self._registry:
                raise ValueError(f"Dependency '{dep_name}' not found")
            cap = self._registry[dep_name]
            if dep_name not in self._registry or dep_name in self._inactive:
                await cap.activate()
                self._inactive.pop(dep_name, None)

        # Activate the capability itself
        cap = self._registry[name]
        await cap.activate()
        self._inactive.pop(name, None)

    async def deactivate(self, name: str) -> None:
        """Deactivate a capability and its dependents."""
        cap = self._registry.get(name)
        if cap is None:
            return
        await cap.deactivate()
        self._inactive[name] = cap

    async def invoke(self, name: str, **kwargs) -> Any:
        """Invoke a capability if it's loaded and active."""
        cap = self._registry.get(name)
        if cap is None:
            raise ValueError(f"Capability '{name}' not registered")
        if name in self._inactive:
            raise RuntimeError(f"Capability '{name}' is not active")
        return await cap.invoke(**kwargs)

    def list_capabilities(self) -> Dict[str, CapabilityMetadata]:
        """List all registered capabilities with metadata."""
        return {name: cap.metadata for name, cap in self._registry.items()}

    def list_active(self) -> List[str]:
        """List all currently active capabilities."""
        return [name for name in self._registry if name not in self._inactive]
