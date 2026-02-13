"""Health checking module."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import asyncio


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health of a single component."""
    component_id: str
    status: HealthStatus
    message: str = ""
    checked_at: datetime = field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = field(default_factory=dict)


class HealthChecker(ABC):
    """Abstract health checker."""
    
    @abstractmethod
    async def check(self) -> ComponentHealth:
        """Perform health check."""
        pass


class SimpleHealthChecker(HealthChecker):
    """Simple health checker."""
    
    def __init__(self, component_id: str):
        self.component_id = component_id
        self.healthy = True
    
    async def check(self) -> ComponentHealth:
        """Check component health."""
        status = HealthStatus.HEALTHY if self.healthy else HealthStatus.UNHEALTHY
        return ComponentHealth(
            component_id=self.component_id,
            status=status,
            message="OK" if self.healthy else "Failed"
        )


class SystemHealthChecker:
    """Checks system health."""
    
    def __init__(self):
        self.checkers: Dict[str, HealthChecker] = {}
        self.last_check: Optional[Dict[str, ComponentHealth]] = None
    
    def register_checker(self, component_id: str, checker: HealthChecker) -> None:
        """Register health checker."""
        self.checkers[component_id] = checker
    
    async def check_all(self) -> Dict[str, ComponentHealth]:
        """Check all components."""
        results = {}
        
        tasks = [
            (cid, checker.check())
            for cid, checker in self.checkers.items()
        ]
        
        for component_id, task in tasks:
            try:
                health = await asyncio.wait_for(task, timeout=5.0)
                results[component_id] = health
            except asyncio.TimeoutError:
                results[component_id] = ComponentHealth(
                    component_id=component_id,
                    status=HealthStatus.UNHEALTHY,
                    message="Health check timeout"
                )
            except Exception as e:
                results[component_id] = ComponentHealth(
                    component_id=component_id,
                    status=HealthStatus.UNHEALTHY,
                    message=str(e)
                )
        
        self.last_check = results
        return results
    
    async def get_overall_status(self) -> HealthStatus:
        """Get overall system health."""
        if not self.last_check:
            await self.check_all()
        
        if not self.last_check:
            return HealthStatus.HEALTHY
        
        statuses = [h.status for h in self.last_check.values()]
        
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    def get_report(self) -> Dict[str, Any]:
        """Get health report."""
        if not self.last_check:
            return {"status": "unknown"}
        
        return {
            "overall_status": "healthy" if all(
                h.status == HealthStatus.HEALTHY for h in self.last_check.values()
            ) else "degraded",
            "components": {
                cid: {
                    "status": health.status.value,
                    "message": health.message,
                    "checked_at": health.checked_at.isoformat(),
                    "details": health.details
                }
                for cid, health in self.last_check.items()
            }
        }
