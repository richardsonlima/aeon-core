from typing import Dict, Any, Optional
from aeon.dispatcher.event import Event, EventType
from aeon.dispatcher.hub import EventHub

class RecoveryHandler:
    """
    Dispatcher Layer (L4) Component for Fluid State Management.
    Replaces rigid DAGs with event-driven recovery loops.
    """
    
    def __init__(self, event_hub: EventHub):
        self.event_hub = event_hub
        self.event_hub.subscribe(EventType.JOB_FAILED, self.handle_failure)

    async def handle_failure(self, event: Event) -> None:
        """
        Catches a job failure and triggers a recovery reasoning cycle.
        """
        error_msg = event.payload.get("error", "Unknown Error")
        job_id = event.payload.get("job_id", "Unknown Job")
        
        print(f" [!] Recovery: Job '{job_id}' failed. Triggering RECOVERY_REQUIRED event.")
        
        from datetime import datetime
        recovery_event = Event(
            event_type=EventType.RECOVERY_REQUIRED,
            timestamp=datetime.now(),
            source="RecoveryHandler",
            priority=10, # High priority
            payload={
                "job_id": job_id,
                "error": error_msg,
                "suggestion": "Re-reasoning path based on DialogueContext"
            }
        )
        
        await self.event_hub.emit(recovery_event)

class StateMemory:
    """
    Dialogue Layer (L3) component for State Persistence.
    Tracks the 'History of Intent' to support recovery.
    """
    def __init__(self):
        self.intent_history = []

    def log_intent(self, intent: str, status: str = "pending"):
        self.intent_history.append({"intent": intent, "status": status})
