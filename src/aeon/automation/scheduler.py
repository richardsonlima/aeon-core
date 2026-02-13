"""
Task Scheduler: Temporal task orchestration engine.
Manages scheduling and execution of tasks based on temporal patterns.
"""

from typing import Dict, Callable, Optional, List
from datetime import datetime
from aeon.automation.temporal import ScheduledTask, TemporalPattern


class TaskScheduler:
    """
    Orchestrates scheduled task execution.
    Manages task registry and provides execution interface.
    """

    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._handlers: Dict[str, Callable] = {}
        self._running = False

    def define_handler(self, handler_id: str, handler: Callable) -> None:
        """Register a handler function for task execution."""
        self._handlers[handler_id] = handler

    def schedule(self, task: ScheduledTask) -> None:
        """Register a new scheduled task."""
        if task.task_id in self._tasks:
            raise ValueError(f"Task '{task.task_id}' already scheduled")
        self._tasks[task.task_id] = task

    def unschedule(self, task_id: str) -> bool:
        """Unschedule a task. Returns True if task was found."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Retrieve a scheduled task by ID."""
        return self._tasks.get(task_id)

    def list_tasks(self) -> List[ScheduledTask]:
        """List all scheduled tasks."""
        return list(self._tasks.values())

    def enable_task(self, task_id: str) -> None:
        """Enable a scheduled task."""
        task = self.get_task(task_id)
        if task:
            task.enabled = True

    def disable_task(self, task_id: str) -> None:
        """Disable a scheduled task."""
        task = self.get_task(task_id)
        if task:
            task.enabled = False

    async def execute_task(self, task_id: str) -> None:
        """Manually trigger execution of a specific task."""
        task = self.get_task(task_id)
        if not task or not task.enabled:
            return
        
        handler = self._handlers.get(task.handler_id)
        if not handler:
            raise ValueError(f"Handler '{task.handler_id}' not found")
        
        try:
            import asyncio
            if asyncio.iscoroutinefunction(handler):
                await handler()
            else:
                handler()
            
            task.last_execution = datetime.now()
            task.execution_count += 1
        except Exception as e:
            print(f"Error executing task '{task_id}': {e}")

    async def start(self) -> None:
        """Start the scheduler."""
        self._running = True

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
