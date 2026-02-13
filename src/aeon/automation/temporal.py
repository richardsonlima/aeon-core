"""
Temporal: Temporal expression and scheduling patterns.
Supports cron-like expressions for flexible scheduling.
"""

from typing import Callable, Optional
from pydantic import BaseModel
from datetime import datetime


class TemporalPattern(BaseModel):
    """
    Temporal expression using cron-like notation.
    Supports flexible scheduling patterns.
    """
    minute: str = "*"      # 0-59 or */N or L or W
    hour: str = "*"        # 0-23 or */N
    day_of_month: str = "*"  # 1-31 or */N or L
    month: str = "*"       # 1-12 or */N
    day_of_week: str = "*" # 0-6 (0=Sunday) or */N
    
    def __str__(self) -> str:
        return f"{self.minute} {self.hour} {self.day_of_month} {self.month} {self.day_of_week}"


class ScheduledTask(BaseModel):
    """
    Represents a scheduled task with temporal trigger.
    Separates scheduling concern from execution.
    """
    task_id: str
    label: str
    temporal_pattern: TemporalPattern
    handler_id: str  # Reference to handler in executor
    enabled: bool = True
    last_execution: Optional[datetime] = None
    execution_count: int = 0
