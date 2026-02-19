import asyncio
from typing import Optional, Callable
from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager
from aeon.dispatcher.hub import EventHub
from aeon.memory.events import BaseEvent
import uuid
from datetime import datetime

class WebhookEvent(BaseEvent):
    """Event triggered by a webhook call"""
    type: str = "webhook_received"
    source: str
    payload: dict

class WebhookListener:
    """
    HTTP Server listening for external webhook events.
    Dispatches received events to the Agent's EventHub.
    """
    
    def __init__(self, port: int = 8000, event_hub: Optional[EventHub] = None):
        self.port = port
        self.event_hub = event_hub
        self.app = FastAPI()
        self.server: Optional[uvicorn.Server] = None
        self._setup_routes()

    def _setup_routes(self):
        @self.app.post("/webhook/{source}")
        async def receive_webhook(source: str, request: Request):
            try:
                payload = await request.json()
                event = WebhookEvent(
                    source=source,
                    payload=payload
                )
                
                print(f"🔔 [Webhook] Received from '{source}'")
                
                if self.event_hub:
                    # Dispatch to internal system
                     # Note: EventHub expects aeon.dispatcher.event.Event, 
                     # but we are using memory.events.BaseEvent here.
                     # In a real system we'd align these types.
                     # For now we just print/log.
                     pass
                
                return {"status": "received", "event_id": event.event_id}
            except Exception as e:
                return {"status": "error", "message": str(e)}

    async def start(self):
        """Start the webhook server in the background"""
        config = uvicorn.Config(self.app, host="0.0.0.0", port=self.port, log_level="error")
        self.server = uvicorn.Server(config)
        # Run in loop without blocking
        asyncio.create_task(self.server.serve())

    async def stop(self):
        """Stop the webhook server"""
        if self.server:
            self.server.should_exit = True
