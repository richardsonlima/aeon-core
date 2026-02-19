"""
Task Scheduler: Temporal task orchestration engine.
Manages scheduling and execution of tasks based on temporal patterns.
"""

from typing import Dict, Callable, Optional, List, Union
from datetime import datetime, timedelta
import asyncio
from croniter import croniter

class ScheduledTask:
    """Represents a task to be executed by the scheduler."""
    def __init__(
        self, 
        task_id: str, 
        handler_id: str, 
        cron: Optional[str] = None, 
        interval_seconds: Optional[int] = None,
        enabled: bool = True
    ):
        self.task_id = task_id
        self.handler_id = handler_id
        self.cron = cron
        self.interval_seconds = interval_seconds
        self.enabled = enabled
        self.last_execution: Optional[datetime] = None
        self.execution_count: int = 0
        self.next_execution: Optional[datetime] = self._calculate_next_run()

    def _calculate_next_run(self) -> datetime:
        now = datetime.now()
        if self.cron:
            return croniter(self.cron, now).get_next(datetime)
        if self.interval_seconds:
            base_time = self.last_execution if self.last_execution else now
            return base_time + timedelta(seconds=self.interval_seconds)
        return now  # Should not happen for valid tasks

class TaskScheduler:
    """
    Orchestrates scheduled task execution with Cron and Interval support.
    Manages task registry and provides execution interface.
    """

    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._handlers: Dict[str, Callable] = {}
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None

    def define_handler(self, handler_id: str, handler: Callable) -> None:
        """Register a handler function for task execution."""
        self._handlers[handler_id] = handler

    def schedule(self, 
        task_id: str, 
        handler_id: str, 
        cron: Optional[str] = None, 
        interval_seconds: Optional[int] = None
    ) -> None:
        """Register a new scheduled task."""
        if not cron and not interval_seconds:
             raise ValueError("Must specify either cron or interval_seconds")
             
        task = ScheduledTask(task_id, handler_id, cron, interval_seconds)
        self._tasks[task_id] = task
        print(f"⏰ [Scheduler] Scheduled '{task_id}' (Next: {task.next_execution})")

    def unschedule(self, task_id: str) -> bool:
        """Unschedule a task. Returns True if task was found."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Retrieve a scheduled task by ID."""
        return self._tasks.get(task_id)

    async def _scheduler_loop(self):
        """Main loop checking for pending tasks."""
        print("⏰ [Scheduler] Started main loop")
        while self._running:
            now = datetime.now()
            for task in self._tasks.values():
                if task.enabled and task.next_execution and now >= task.next_execution:
                    # Trigger task
                    asyncio.create_task(self.execute_task(task.task_id))
                    
                    # Schedule next run
                    task.last_execution = now
                    try:
                        task.next_execution = task._calculate_next_run()
                    except Exception as e:
                        print(f" [!] Error calculating next run for {task.task_id}: {e}")
                        task.enabled = False

            await asyncio.sleep(1) # Check every second

    async def execute_task(self, task_id: str) -> None:
        """Manually trigger execution of a specific task."""
        task = self.get_task(task_id)
        if not task:
            return
        
        handler = self._handlers.get(task.handler_id)
        if not handler:
            print(f" [!] Handler '{task.handler_id}' not found")
            return
        
        try:
            # print(f"⚙️ [Scheduler] Executing '{task_id}'")
            if asyncio.iscoroutinefunction(handler):
                await handler()
            else:
                handler()
            
            task.execution_count += 1
        except Exception as e:
            print(f"Error executing task '{task_id}': {e}")

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return
            
        self._running = True
        self._loop_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

