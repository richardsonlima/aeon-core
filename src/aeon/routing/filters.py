"""Message filtering - pattern and logic-based message filtering."""

from abc import ABC, abstractmethod
from typing import Any, List, Pattern, Callable, Dict
import re


class MessageFilter(ABC):
    """Abstract message filter."""
    
    @abstractmethod
    async def matches(self, message: Any) -> bool:
        """Check if message matches filter criteria."""
        pass


class PatternFilter(MessageFilter):
    """Filters messages by regex pattern."""
    
    def __init__(self, pattern: str, field: str = "content"):
        self.pattern = re.compile(pattern)
        self.field = field
    
    async def matches(self, message: Any) -> bool:
        """Match against pattern."""
        value = getattr(message, self.field, str(message))
        return bool(self.pattern.search(str(value)))


class TypeFilter(MessageFilter):
    """Filters by message type."""
    
    def __init__(self, *types):
        self.types = types
    
    async def matches(self, message: Any) -> bool:
        """Match by type."""
        return type(message) in self.types


class PredicateFilter(MessageFilter):
    """Filters using custom predicate function."""
    
    def __init__(self, predicate: Callable[[Any], bool]):
        self.predicate = predicate
    
    async def matches(self, message: Any) -> bool:
        """Apply predicate."""
        return self.predicate(message)


class AttributeFilter(MessageFilter):
    """Filters by message attributes."""
    
    def __init__(self, **conditions: Any):
        self.conditions = conditions
    
    async def matches(self, message: Any) -> bool:
        """Match attributes."""
        for attr, expected in self.conditions.items():
            actual = getattr(message, attr, None)
            if actual != expected:
                return False
        return True


class FilterChain(MessageFilter):
    """Chains multiple filters with AND/OR logic."""
    
    def __init__(self, filters: List[MessageFilter], mode: str = "AND"):
        self.filters = filters
        self.mode = mode.upper()
        if self.mode not in ("AND", "OR"):
            raise ValueError("mode must be AND or OR")
    
    async def matches(self, message: Any) -> bool:
        """Apply filter chain."""
        if not self.filters:
            return True
        
        if self.mode == "AND":
            for filter in self.filters:
                if not await filter.matches(message):
                    return False
            return True
        else:  # OR
            for filter in self.filters:
                if await filter.matches(message):
                    return True
            return False


class RangeFilter(MessageFilter):
    """Filters by value range."""
    
    def __init__(self, field: str, min_val: Any = None, max_val: Any = None):
        self.field = field
        self.min_val = min_val
        self.max_val = max_val
    
    async def matches(self, message: Any) -> bool:
        """Match within range."""
        value = getattr(message, self.field, None)
        if value is None:
            return False
        
        if self.min_val is not None and value < self.min_val:
            return False
        if self.max_val is not None and value > self.max_val:
            return False
        
        return True
