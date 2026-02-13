"""
Routing Module - Intelligent message routing and dispatch.

This module provides sophisticated message routing, filtering, and prioritization
across agent layers and integrations. Enterprise-grade routing with flexible strategies
for optimal performance and reliability.
"""

from .router import Router, Route, RouteMatch, RoutingContext
from .strategies import RoutingStrategy, PriorityStrategy, LoadBalancedStrategy
from .filters import MessageFilter, FilterChain, PatternFilter
from .distributor import MessageDistributor, DistributionPolicy

__all__ = [
    "Router",
    "Route",
    "RouteMatch",
    "RoutingContext",
    "RoutingStrategy",
    "PriorityStrategy",
    "LoadBalancedStrategy",
    "MessageFilter",
    "FilterChain",
    "PatternFilter",
    "MessageDistributor",
    "DistributionPolicy",
]
