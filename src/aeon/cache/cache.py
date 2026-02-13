"""Core cache implementation."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class CachingStrategy(Enum):
    """Cache replacement strategies."""
    LRU = "lru"          # Least Recently Used
    LFU = "lfu"          # Least Frequently Used
    FIFO = "fifo"        # First In First Out
    TTL = "ttl"          # Time To Live


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    ttl_seconds: Optional[int] = None
    access_count: int = 0
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl_seconds is None:
            return False
        
        elapsed = (datetime.utcnow() - self.created_at).total_seconds()
        return elapsed > self.ttl_seconds
    
    def touch(self) -> None:
        """Update access time."""
        self.accessed_at = datetime.utcnow()
        self.access_count += 1


class Cache(ABC):
    """Abstract cache."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set value in cache."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear entire cache."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass


class SimpleCache(Cache):
    """Simple in-memory cache."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.store: Dict[str, CacheEntry] = {}
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0
        }
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        entry = self.store.get(key)
        
        if entry is None:
            self.stats["misses"] += 1
            return None
        
        if entry.is_expired():
            del self.store[key]
            self.stats["misses"] += 1
            return None
        
        entry.touch()
        self.stats["hits"] += 1
        return entry.value
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set value in cache."""
        if len(self.store) >= self.max_size and key not in self.store:
            # Simple eviction: remove oldest entry
            if self.store:
                oldest_key = min(
                    self.store.keys(),
                    key=lambda k: self.store[k].accessed_at
                )
                del self.store[oldest_key]
                self.stats["evictions"] += 1
        
        self.store[key] = CacheEntry(
            key=key,
            value=value,
            ttl_seconds=ttl_seconds
        )
        self.stats["sets"] += 1
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if key in self.store:
            del self.store[key]
            self.stats["deletes"] += 1
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        entry = self.store.get(key)
        if entry and not entry.is_expired():
            return True
        elif entry and entry.is_expired():
            del self.store[key]
        return False
    
    async def clear(self) -> None:
        """Clear entire cache."""
        self.store.clear()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            **self.stats,
            "size": len(self.store),
            "max_size": self.max_size,
            "hit_rate": hit_rate,
            "total_requests": total
        }


class CacheDecorator:
    """Decorator for caching function results."""
    
    def __init__(self, cache: Cache, ttl_seconds: Optional[int] = None):
        self.cache = cache
        self.ttl_seconds = ttl_seconds
    
    def __call__(self, func: Callable) -> Callable:
        """Decorate function."""
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{args}:{kwargs}"
            
            # Try to get from cache
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cached
            
            # Call function and cache result
            result = await func(*args, **kwargs)
            await self.cache.set(cache_key, result, self.ttl_seconds)
            
            return result
        
        return wrapper
