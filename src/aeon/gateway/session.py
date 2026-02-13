"""Session management for gateway."""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from enum import Enum
import uuid
import logging

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """Session lifecycle states."""
    ACTIVE = "active"
    IDLE = "idle"
    SUSPENDED = "suspended"
    CLOSED = "closed"


@dataclass
class Session:
    """Represents a user/agent session."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    connection_id: str = ""
    state: SessionState = SessionState.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)
    message_count: int = 0
    
    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if session has expired."""
        elapsed = (datetime.utcnow() - self.last_activity).total_seconds()
        return elapsed > ttl_seconds
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "connection_id": self.connection_id,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "metadata": self.metadata,
            "message_count": self.message_count
        }


class SessionManager:
    """Manages user sessions."""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.sessions: Dict[str, Session] = {}
        self.ttl_seconds = ttl_seconds
        self.stats = {
            "total_created": 0,
            "total_closed": 0,
            "current_active": 0
        }
    
    def create_session(self, connection_id: str, metadata: Optional[Dict] = None) -> Session:
        """Create new session."""
        session = Session(
            connection_id=connection_id,
            metadata=metadata or {}
        )
        self.sessions[session.session_id] = session
        self.stats["total_created"] += 1
        self.stats["current_active"] = len([s for s in self.sessions.values() if s.state == SessionState.ACTIVE])
        logger.info(f"Session created: {session.session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        return self.sessions.get(session_id)
    
    def update_session(self, session_id: str, data: Dict[str, Any]) -> Optional[Session]:
        """Update session data."""
        session = self.sessions.get(session_id)
        if session:
            session.data.update(data)
            session.update_activity()
            session.message_count += 1
        return session
    
    def close_session(self, session_id: str) -> bool:
        """Close a session."""
        session = self.sessions.get(session_id)
        if session:
            session.state = SessionState.CLOSED
            self.stats["total_closed"] += 1
            self.stats["current_active"] = len([s for s in self.sessions.values() if s.state == SessionState.ACTIVE])
            logger.info(f"Session closed: {session_id}")
            return True
        return False
    
    def suspend_session(self, session_id: str) -> bool:
        """Suspend a session (without closing)."""
        session = self.sessions.get(session_id)
        if session:
            session.state = SessionState.SUSPENDED
            logger.info(f"Session suspended: {session_id}")
            return True
        return False
    
    def cleanup_expired(self) -> List[str]:
        """Clean up expired sessions."""
        expired = []
        for session_id, session in list(self.sessions.items()):
            if session.is_expired(self.ttl_seconds):
                self.close_session(session_id)
                expired.append(session_id)
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
        
        return expired
    
    def get_sessions_by_connection(self, connection_id: str) -> List[Session]:
        """Get all sessions for a connection."""
        return [s for s in self.sessions.values() if s.connection_id == connection_id]
    
    def get_all_active(self) -> List[Session]:
        """Get all active sessions."""
        return [s for s in self.sessions.values() if s.state == SessionState.ACTIVE]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        return {
            **self.stats,
            "total_sessions": len(self.sessions),
            "active_sessions": len(self.get_all_active()),
            "suspended_sessions": len([s for s in self.sessions.values() if s.state == SessionState.SUSPENDED])
        }


class SessionStore:
    """Persistent session storage."""
    
    def __init__(self):
        self.store: Dict[str, Dict[str, Any]] = {}
    
    async def save(self, session: Session) -> None:
        """Save session to store."""
        self.store[session.session_id] = session.to_dict()
    
    async def load(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session from store."""
        return self.store.get(session_id)
    
    async def delete(self, session_id: str) -> None:
        """Delete session from store."""
        if session_id in self.store:
            del self.store[session_id]
    
    async def clear_expired(self, ttl_seconds: int) -> int:
        """Clear expired sessions."""
        cutoff_time = datetime.utcnow() - timedelta(seconds=ttl_seconds)
        expired_count = 0
        
        for session_id, data in list(self.store.items()):
            last_activity = datetime.fromisoformat(data.get("last_activity", "1970-01-01T00:00:00"))
            if last_activity < cutoff_time:
                del self.store[session_id]
                expired_count += 1
        
        return expired_count
