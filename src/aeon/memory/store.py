from typing import List, Dict, Any, Optional
from aeon.memory.events import BaseEvent
from aeon.memory.models import Base, EventModel
from sqlalchemy import create_engine, select, desc
from sqlalchemy.orm import sessionmaker, Session
import json
import os

class EventStore:
    """
    Persistent store for agent history using SQLite.
    Serves as the 'Long-Term Memory' of the autonomous agent.
    """
    
    def __init__(self, db_path: str = "aeon_memory.db"):
        self.db_url = f"sqlite:///{db_path}"
        self.engine = create_engine(self.db_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def append(self, event: BaseEvent) -> None:
        """Record a new event in persistent history"""
        session: Session = self.SessionLocal()
        try:
            # Extract basic fields
            db_event = EventModel(
                event_id=str(event.event_id),
                timestamp=event.timestamp,
                event_type=event.type,
                payload=event.model_dump(mode='json')
            )
            
            # Enrich with specific fields for indexing if available
            if hasattr(event, 'agent_name'):
                db_event.agent_name = event.agent_name # type: ignore
            if hasattr(event, 'tool_name'):
                db_event.tool_name = event.tool_name # type: ignore
            if hasattr(event, 'content'):
                # Store first 100 chars of content for preview/search
                db_event.content_preview = str(event.content)[:100] # type: ignore

            session.add(db_event)
            session.commit()
            # print(f"💾 [DB] Saved: {event.type}")
        except Exception as e:
            print(f" [!] Database Error: {e}")
            session.rollback()
        finally:
            session.close()

    def get_history(self, limit: int = 100) -> List[BaseEvent]:
        """Retrieve full event history (most recent first by default for efficiency)"""
        session: Session = self.SessionLocal()
        try:
            stmt = select(EventModel).order_by(EventModel.timestamp.asc()).limit(limit)
            rows = session.execute(stmt).scalars().all()
            
            # Reconstruct BaseEvent objects (generic reconstruction)
            # In a real system, we might want to cast back to specific Event classes
            events = []
            for row in rows:
                # We reuse the BaseEvent base but inject raw data
                # Ideally we map 'type' back to specific classes, but for now generic is fine
                # or strictly we just return the payload as a dict wrapped in an object
                
                # Simple reconstruction:
                event = BaseEvent(**row.payload)
                events.append(event)
            return events
        finally:
            session.close()

    def get_recent(self, limit: int = 10) -> List[BaseEvent]:
        """Retrieve most recent events"""
        session: Session = self.SessionLocal()
        try:
            stmt = select(EventModel).order_by(EventModel.timestamp.desc()).limit(limit)
            rows = session.execute(stmt).scalars().all()
            # Return in chronological order for context window
            return [BaseEvent(**r.payload) for r in reversed(list(rows))]
        finally:
            session.close()

    def to_json(self) -> str:
        """Export recent memory state to JSON"""
        events = self.get_history(limit=1000)
        return json.dumps([e.model_dump(mode='json') for e in events], indent=2)

