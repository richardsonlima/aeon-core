"""
Automation Module: Temporal Task Orchestration.
Manages recurring and scheduled task execution with pattern-based scheduling.
Architecture: Trigger-Action Framework with Temporal Expressions.
"""

from aeon.automation.scheduler import TaskScheduler
from aeon.automation.temporal import TemporalPattern, ScheduledTask

__all__ = ["TaskScheduler", "TemporalPattern", "ScheduledTask"]
