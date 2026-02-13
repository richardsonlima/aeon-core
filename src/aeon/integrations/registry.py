"""
Provider Registry: Manages available transport integrations.
Implements the Registry Pattern for dynamic provider discovery.
"""

from typing import Dict, Optional, List
from aeon.integrations.provider import IntegrationProvider, Packet


class ProviderRegistry:
    """
    Central registry for transport providers.
    Handles provider lifecycle and packet routing.
    """

    def __init__(self):
        self._providers: Dict[str, IntegrationProvider] = {}
        self._active_providers: set = set()

    def register(self, name: str, provider: IntegrationProvider) -> None:
        """Register a new transport provider."""
        if name in self._providers:
            raise ValueError(f"Provider '{name}' already registered")
        self._providers[name] = provider

    def unregister(self, name: str) -> None:
        """Unregister a transport provider."""
        if name in self._providers:
            del self._providers[name]
            self._active_providers.discard(name)

    def get(self, name: str) -> Optional[IntegrationProvider]:
        """Retrieve a provider by name."""
        return self._providers.get(name)

    def list_providers(self) -> List[str]:
        """List all registered provider names."""
        return list(self._providers.keys())

    async def dispatch_packet(self, provider_name: str, packet: Packet) -> bool:
        """Route a packet through a specific provider."""
        provider = self.get(provider_name)
        if provider is None:
            raise ValueError(f"Provider '{provider_name}' not found")
        if not provider.config.enabled:
            raise ValueError(f"Provider '{provider_name}' is disabled")
        return await provider.dispatch(packet)

    async def activate_provider(self, name: str) -> None:
        """Activate a provider and initialize its connection."""
        provider = self.get(name)
        if provider is None:
            raise ValueError(f"Provider '{name}' not found")
        await provider.initialize()
        self._active_providers.add(name)

    async def deactivate_provider(self, name: str) -> None:
        """Deactivate a provider and close its connection."""
        provider = self.get(name)
        if provider is None:
            return
        await provider.terminate()
        self._active_providers.discard(name)

    async def activate_all(self) -> None:
        """Activate all enabled providers."""
        for name, provider in self._providers.items():
            if provider.config.enabled:
                await self.activate_provider(name)

    async def deactivate_all(self) -> None:
        """Deactivate all active providers."""
        for name in list(self._active_providers):
            await self.deactivate_provider(name)

    def is_active(self, name: str) -> bool:
        """Check if a provider is currently active."""
        return name in self._active_providers
