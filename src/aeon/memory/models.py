from datetime import datetime
from typing import Any, Dict
from sqlalchemy import Column, String, Integer, DateTime, JSON, Text
from sqlalchemy.orm import declarative_base
import uuid

Base = declarative_base()

class EventModel(Base):
    """
    SQLAlchemy model for storing agent events.
    """
    __tablename__ = 'agent_events'

    event_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String, nullable=False, index=True)
    agent_name = Column(String, nullable=True, index=True)
    
    # Store the full event data as JSON
    payload = Column(JSON, nullable=False)
    
    # Optional searchable fields extracted from payload
    tool_name = Column(String, nullable=True)
    content_preview = Column(Text, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "type": self.event_type,
            "agent_name": self.agent_name,
            "payload": self.payload
        }
