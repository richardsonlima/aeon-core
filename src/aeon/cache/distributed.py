"""Distributed cache implementation."""

from typing import Any, Dict, Optional
from .cache import Cache, CacheEntry


class DistributedCache(Cache):
    """Distributed cache for multi-node systems."""
    
    def __init__(self):
        self.local_store: Dict[str, CacheEntry] = {}
        self.remote_nodes: Dict[str, Any] = {}
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "local": 0,
            "remote": 0
        }
    
    def register_node(self, node_id: str, node: Any) -> None:
        """Register remote cache node."""
        self.remote_nodes[node_id] = node
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from local or remote cache."""
        # Try local cache first
        entry = self.local_store.get(key)
        if entry and not entry.is_expired():
            entry.touch()
            self.stats["hits"] += 1
            self.stats["local"] += 1
            return entry.value
        
        # Try remote nodes
        for node_id, node in self.remote_nodes.items():
            try:
                value = await node.get(key)
                if value is not None:
                    self.stats["hits"] += 1
                    self.stats["remote"] += 1
                    return value
            except:
                continue
        
        self.stats["misses"] += 1
        return None
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set value in local cache and replicate to remote."""
        entry = CacheEntry(
            key=key,
            value=value,
            ttl_seconds=ttl_seconds
        )
        self.local_store[key] = entry
        self.stats["sets"] += 1
        
        # Replicate to remote nodes
        for node in self.remote_nodes.values():
            try:
                await node.set(key, value, ttl_seconds)
            except:
                pass  # Continue if replication fails
    
    async def delete(self, key: str) -> bool:
        """Delete from local and remote cache."""
        deleted = False
        
        if key in self.local_store:
            del self.local_store[key]
            deleted = True
        
        # Delete from remote nodes
        for node in self.remote_nodes.values():
            try:
                await node.delete(key)
            except:
                pass
        
        if deleted:
            self.stats["deletes"] += 1
        
        return deleted
    
    async def exists(self, key: str) -> bool:
        """Check if exists in any node."""
        # Check local
        entry = self.local_store.get(key)
        if entry and not entry.is_expired():
            return True
        elif entry and entry.is_expired():
            del self.local_store[key]
        
        # Check remote
        for node in self.remote_nodes.values():
            try:
                if await node.exists(key):
                    return True
            except:
                continue
        
        return False
    
    async def clear(self) -> None:
        """Clear all caches."""
        self.local_store.clear()
        
        for node in self.remote_nodes.values():
            try:
                await node.clear()
            except:
                pass
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            **self.stats,
            "local_entries": len(self.local_store),
            "remote_nodes": len(self.remote_nodes),
            "hit_rate": hit_rate,
            "total_requests": total
        }
