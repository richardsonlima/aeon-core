"""
Extensions Module: Capability Framework.
Implements a pluggable extension system for modular functionality.
Architecture: Plugin Loading with Dependency Resolution.
"""

from aeon.extensions.capability import Capability
from aeon.extensions.loader import CapabilityLoader

__all__ = ["Capability", "CapabilityLoader"]
