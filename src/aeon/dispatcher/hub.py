"""
Event Hub: Central event routing and dispatch system.
Implements observer pattern with priority-based event processing.
"""

import asyncio
from typing import Callable, List, Dict, Optional
from aeon.dispatcher.event import Event, EventType


class EventHub:
    """
    Central message hub for decoupled component communication.
    Manages subscribers and event propagation with priority handling.
    """

    def __init__(self, max_queue_size: int = 1000):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._wildcard_subscribers: List[Callable] = []
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._running = False

    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        """Subscribe to a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def subscribe_all(self, handler: Callable) -> None:
        """Subscribe to all events (wildcard subscription)."""
        self._wildcard_subscribers.append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable) -> None:
        """Unsubscribe from a specific event type."""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)

    async def emit(self, event: Event) -> None:
        """
        Emit an event to all subscribers.
        Queues event for async processing.
        """
        await self._event_queue.put(event)

    async def _process_queue(self) -> None:
        """Process queued events in priority order."""
        events = []
        
        # Collect all pending events
        while not self._event_queue.empty():
            try:
                events.append(self._event_queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        
        # Sort by priority (descending)
        events.sort(key=lambda e: e.priority, reverse=True)
        
        # Process events
        for event in events:
            await self._dispatch(event)

    async def _dispatch(self, event: Event) -> None:
        """Dispatch an event to all relevant handlers."""
        handlers = self._subscribers.get(event.event_type, [])
        handlers.extend(self._wildcard_subscribers)
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                print(f"Error in event handler: {e}")

    async def start(self) -> None:
        """Start the event processing loop."""
        self._running = True
        while self._running:
            await self._process_queue()
            await asyncio.sleep(0.01)  # Yield control

    async def stop(self) -> None:
        """Stop the event processing loop."""
        self._running = False
