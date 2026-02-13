"""Router implementation - core routing engine."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Pattern, Any, Callable
from enum import Enum
import re
from datetime import datetime


class RouteMatchType(Enum):
    """Types of route matches."""
    EXACT = "exact"
    PREFIX = "prefix"
    PATTERN = "pattern"
    PREDICATE = "predicate"


@dataclass
class RouteMatch:
    """Result of route matching."""
    matched: bool
    route_id: Optional[str] = None
    match_type: Optional[RouteMatchType] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0  # 0.0 to 1.0


@dataclass
class RoutingContext:
    """Context for routing decisions."""
    source: str
    destination: str
    message_type: str
    priority: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: set = field(default_factory=set)


@dataclass
class Route:
    """Single routing rule."""
    route_id: str
    matcher: Callable[[RoutingContext], RouteMatch]
    handler: Callable[[Any], None]
    priority: int = 0
    enabled: bool = True
    max_attempts: int = 3
    timeout_ms: int = 5000
    fallback: Optional[Callable[[Any, Exception], None]] = None


class Router:
    """
    Intelligent message router with pattern matching and priorities.
    
    Features:
    - Pattern-based routing
    - Priority-aware dispatch
    - Fallback mechanisms
    - Route statistics and monitoring
    """
    
    def __init__(self):
        self.routes: Dict[str, Route] = {}
        self.stats = {
            "total_routed": 0,
            "successful": 0,
            "failed": 0,
            "bypassed": 0,
            "routes": {}
        }
    
    def register(self, route: Route) -> None:
        """Register a new route."""
        if route.route_id in self.routes:
            raise ValueError(f"Route {route.route_id} already registered")
        self.routes[route.route_id] = route
        self.stats["routes"][route.route_id] = {
            "called": 0,
            "success": 0,
            "failed": 0
        }
    
    def unregister(self, route_id: str) -> None:
        """Unregister a route."""
        if route_id in self.routes:
            del self.routes[route_id]
            if route_id in self.stats["routes"]:
                del self.stats["routes"][route_id]
    
    def find_routes(self, context: RoutingContext) -> List[Route]:
        """Find matching routes for context."""
        matches = []
        for route in sorted(
            self.routes.values(),
            key=lambda r: r.priority,
            reverse=True
        ):
            if not route.enabled:
                continue
            
            match = route.matcher(context)
            if match.matched:
                matches.append(route)
        
        return matches
    
    async def route(self, context: RoutingContext, message: Any) -> bool:
        """
        Route a message based on context.
        
        Returns True if routing succeeded, False otherwise.
        """
        self.stats["total_routed"] += 1
        matches = self.find_routes(context)
        
        if not matches:
            self.stats["bypassed"] += 1
            return False
        
        for route in matches:
            self.stats["routes"][route.route_id]["called"] += 1
            
            for attempt in range(1, route.max_attempts + 1):
                try:
                    await route.handler(message)
                    self.stats["routes"][route.route_id]["success"] += 1
                    self.stats["successful"] += 1
                    return True
                except Exception as e:
                    if attempt == route.max_attempts:
                        if route.fallback:
                            try:
                                await route.fallback(message, e)
                            except:
                                pass
                        self.stats["routes"][route.route_id]["failed"] += 1
                        self.stats["failed"] += 1
        
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        return {
            **self.stats,
            "routes_registered": len(self.routes),
            "success_rate": (
                self.stats["successful"] / self.stats["total_routed"]
                if self.stats["total_routed"] > 0 else 0
            )
        }
