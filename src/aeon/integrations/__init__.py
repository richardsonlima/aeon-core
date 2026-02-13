"""
Integrations Module: Platform Connectors.
Enables seamless interaction with external communication platforms.
Architecture: Abstract Transport Layer with Provider-based routing.
"""

from aeon.integrations.provider import IntegrationProvider, ProviderConfig
from aeon.integrations.registry import ProviderRegistry

__all__ = ["IntegrationProvider", "ProviderConfig", "ProviderRegistry"]
