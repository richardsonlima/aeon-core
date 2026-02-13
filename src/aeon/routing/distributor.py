"""Message distributor - distributes messages to multiple targets."""

from enum import Enum
from typing import List, Callable, Any, Dict
from dataclasses import dataclass
import asyncio


class DistributionPolicy(Enum):
    """Message distribution policies."""
    BROADCAST = "broadcast"      # Send to all
    FANOUT = "fanout"            # Send to all, await all
    SCATTER = "scatter"          # Send to all, fire and forget
    ROUNDROBIN = "roundrobin"    # Send to one in rotation
    RANDOM = "random"            # Send to random one
    BALANCED = "balanced"        # Send to least loaded


@dataclass
class DistributionResult:
    """Result of message distribution."""
    policy: DistributionPolicy
    targets_count: int
    successful: int
    failed: int
    errors: Dict[str, Exception]


class MessageDistributor:
    """
    Distributes messages to multiple targets based on policy.
    
    Useful for:
    - Broadcasting to all integrations
    - Load balancing across providers
    - Cascading fallbacks
    """
    
    def __init__(self):
        self.targets: Dict[str, Callable] = {}
        self.load: Dict[str, int] = {}
    
    def register_target(self, target_id: str, handler: Callable) -> None:
        """Register a distribution target."""
        self.targets[target_id] = handler
        self.load[target_id] = 0
    
    def unregister_target(self, target_id: str) -> None:
        """Unregister a target."""
        if target_id in self.targets:
            del self.targets[target_id]
            if target_id in self.load:
                del self.load[target_id]
    
    async def distribute(
        self,
        message: Any,
        policy: DistributionPolicy = DistributionPolicy.BROADCAST,
        timeout: float = 5.0
    ) -> DistributionResult:
        """Distribute message based on policy."""
        result = DistributionResult(
            policy=policy,
            targets_count=len(self.targets),
            successful=0,
            failed=0,
            errors={}
        )
        
        if not self.targets:
            return result
        
        if policy == DistributionPolicy.BROADCAST:
            result = await self._broadcast(message, timeout)
        elif policy == DistributionPolicy.FANOUT:
            result = await self._fanout(message, timeout)
        elif policy == DistributionPolicy.SCATTER:
            result = await self._scatter(message)
        elif policy == DistributionPolicy.ROUNDROBIN:
            result = await self._roundrobin(message, timeout)
        elif policy == DistributionPolicy.RANDOM:
            result = await self._random(message, timeout)
        elif policy == DistributionPolicy.BALANCED:
            result = await self._balanced(message, timeout)
        
        result.policy = policy
        return result
    
    async def _broadcast(self, message: Any, timeout: float) -> DistributionResult:
        """Broadcast to all targets, return immediately."""
        result = DistributionResult(
            policy=DistributionPolicy.BROADCAST,
            targets_count=len(self.targets),
            successful=0,
            failed=0,
            errors={}
        )
        
        for target_id, handler in self.targets.items():
            try:
                asyncio.create_task(handler(message))
                result.successful += 1
            except Exception as e:
                result.errors[target_id] = e
                result.failed += 1
        
        return result
    
    async def _fanout(self, message: Any, timeout: float) -> DistributionResult:
        """Send to all targets and wait for all."""
        result = DistributionResult(
            policy=DistributionPolicy.FANOUT,
            targets_count=len(self.targets),
            successful=0,
            failed=0,
            errors={}
        )
        
        tasks = []
        for target_id, handler in self.targets.items():
            tasks.append((target_id, handler(message)))
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*[t[1] for t in tasks], return_exceptions=True),
                timeout=timeout
            )
            
            for (target_id, _), res in zip(tasks, results):
                if isinstance(res, Exception):
                    result.errors[target_id] = res
                    result.failed += 1
                else:
                    result.successful += 1
        except asyncio.TimeoutError:
            result.failed = len(tasks)
            result.errors["*"] = TimeoutError("Distribution timeout")
        
        return result
    
    async def _scatter(self, message: Any) -> DistributionResult:
        """Fire and forget to all targets."""
        result = DistributionResult(
            policy=DistributionPolicy.SCATTER,
            targets_count=len(self.targets),
            successful=len(self.targets),
            failed=0,
            errors={}
        )
        
        for handler in self.targets.values():
            asyncio.create_task(handler(message))
        
        return result
    
    async def _roundrobin(self, message: Any, timeout: float) -> DistributionResult:
        """Send to next target in rotation."""
        result = DistributionResult(
            policy=DistributionPolicy.ROUNDROBIN,
            targets_count=len(self.targets),
            successful=0,
            failed=0,
            errors={}
        )
        
        if not self.targets:
            return result
        
        target_ids = list(self.targets.keys())
        idx = hash(message) % len(target_ids)
        target_id = target_ids[idx]
        
        try:
            await asyncio.wait_for(
                self.targets[target_id](message),
                timeout=timeout
            )
            result.successful = 1
        except Exception as e:
            result.errors[target_id] = e
            result.failed = 1
        
        return result
    
    async def _random(self, message: Any, timeout: float) -> DistributionResult:
        """Send to random target."""
        import random
        
        result = DistributionResult(
            policy=DistributionPolicy.RANDOM,
            targets_count=len(self.targets),
            successful=0,
            failed=0,
            errors={}
        )
        
        if not self.targets:
            return result
        
        target_id = random.choice(list(self.targets.keys()))
        
        try:
            await asyncio.wait_for(
                self.targets[target_id](message),
                timeout=timeout
            )
            result.successful = 1
        except Exception as e:
            result.errors[target_id] = e
            result.failed = 1
        
        return result
    
    async def _balanced(self, message: Any, timeout: float) -> DistributionResult:
        """Send to least loaded target."""
        result = DistributionResult(
            policy=DistributionPolicy.BALANCED,
            targets_count=len(self.targets),
            successful=0,
            failed=0,
            errors={}
        )
        
        if not self.targets:
            return result
        
        target_id = min(self.load.keys(), key=lambda k: self.load[k])
        self.load[target_id] += 1
        
        try:
            await asyncio.wait_for(
                self.targets[target_id](message),
                timeout=timeout
            )
            result.successful = 1
        except Exception as e:
            result.errors[target_id] = e
            result.failed = 1
        finally:
            self.load[target_id] -= 1
        
        return result
