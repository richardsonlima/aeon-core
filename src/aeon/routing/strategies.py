"""Routing strategies - different algorithms for route selection."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from .router import Route, RoutingContext
from dataclasses import dataclass


class RoutingStrategy(ABC):
    """Abstract base for routing strategies."""
    
    @abstractmethod
    async def select(self, context: RoutingContext, candidates: List[Route]) -> Route:
        """Select best route from candidates."""
        pass


class PriorityStrategy(RoutingStrategy):
    """Routes based on priority order."""
    
    async def select(self, context: RoutingContext, candidates: List[Route]) -> Route:
        """Select highest priority route."""
        if not candidates:
            raise ValueError("No candidates available")
        return sorted(candidates, key=lambda r: r.priority, reverse=True)[0]


class LoadBalancedStrategy(RoutingStrategy):
    """Distributes load evenly across routes."""
    
    def __init__(self):
        self.route_loads: Dict[str, int] = {}
    
    async def select(self, context: RoutingContext, candidates: List[Route]) -> Route:
        """Select route with lowest current load."""
        if not candidates:
            raise ValueError("No candidates available")
        
        # Initialize if needed
        for route in candidates:
            if route.route_id not in self.route_loads:
                self.route_loads[route.route_id] = 0
        
        # Select route with minimum load
        selected = min(candidates, key=lambda r: self.route_loads[r.route_id])
        self.route_loads[selected.route_id] += 1
        return selected
    
    def decrement_load(self, route_id: str) -> None:
        """Decrement load for route after processing."""
        if route_id in self.route_loads:
            self.route_loads[route_id] = max(0, self.route_loads[route_id] - 1)


class WeightedRandomStrategy(RoutingStrategy):
    """Routes randomly with weight-based probability."""
    
    import random
    
    async def select(self, context: RoutingContext, candidates: List[Route]) -> Route:
        """Select route based on weighted probability."""
        if not candidates:
            raise ValueError("No candidates available")
        
        # Use priority as weight
        weights = [r.priority for r in candidates]
        total_weight = sum(weights)
        
        if total_weight <= 0:
            # Equal probability
            return self.random.choice(candidates)
        
        # Weighted random selection
        import random
        choice = random.uniform(0, total_weight)
        current = 0
        for route, weight in zip(candidates, weights):
            current += weight
            if choice <= current:
                return route
        
        return candidates[-1]


class RoundRobinStrategy(RoutingStrategy):
    """Routes in round-robin fashion."""
    
    def __init__(self):
        self.current_index = 0
    
    async def select(self, context: RoutingContext, candidates: List[Route]) -> Route:
        """Select next route in round-robin order."""
        if not candidates:
            raise ValueError("No candidates available")
        
        selected = candidates[self.current_index % len(candidates)]
        self.current_index += 1
        return selected


class ContextAwareStrategy(RoutingStrategy):
    """Routes based on context properties."""
    
    def __init__(self, context_mapper=None):
        self.context_mapper = context_mapper or self._default_mapper
    
    def _default_mapper(self, context: RoutingContext) -> str:
        """Default context to route mapping."""
        return context.source
    
    async def select(self, context: RoutingContext, candidates: List[Route]) -> Route:
        """Select route based on context."""
        if not candidates:
            raise ValueError("No candidates available")
        
        context_key = self.context_mapper(context)
        
        # Try to match route by context
        for route in candidates:
            if context_key in route.route_id or context_key in str(route.metadata):
                return route
        
        # Fallback to first
        return candidates[0]
