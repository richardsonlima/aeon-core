"""LRU cache implementation."""

from typing import Any, Dict, Optional
from collections import OrderedDict
from .cache import Cache, CacheEntry


class LRUCache(Cache):
    """Least Recently Used cache."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.store: OrderedDict[str, CacheEntry] = OrderedDict()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0
        }
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value, promoting to most recent."""
        entry = self.store.get(key)
        
        if entry is None:
            self.stats["misses"] += 1
            return None
        
        if entry.is_expired():
            del self.store[key]
            self.stats["misses"] += 1
            return None
        
        # Move to end (most recently used)
        self.store.move_to_end(key)
        entry.touch()
        self.stats["hits"] += 1
        
        return entry.value
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set value, evicting LRU if needed."""
        if key in self.store:
            # Update existing entry
            self.store.move_to_end(key)
        elif len(self.store) >= self.max_size:
            # Evict least recently used (first item)
            lru_key = next(iter(self.store))
            del self.store[lru_key]
            self.stats["evictions"] += 1
        
        self.store[key] = CacheEntry(
            key=key,
            value=value,
            ttl_seconds=ttl_seconds
        )
        self.stats["sets"] += 1
    
    async def delete(self, key: str) -> bool:
        """Delete value."""
        if key in self.store:
            del self.store[key]
            self.stats["deletes"] += 1
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists and not expired."""
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
