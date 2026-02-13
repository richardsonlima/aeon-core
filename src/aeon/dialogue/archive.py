"""
Dialogue Archive: Persistent storage for conversation contexts.
Implements retention policies and queryable conversation history.
"""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
from aeon.dialogue.context import DialogueContext


class DialogueArchive:
    """
    Persistent storage for dialogue contexts.
    Provides archival, retrieval, and cleanup capabilities.
    """

    def __init__(self, retention_days: int = 30):
        self._contexts: Dict[str, DialogueContext] = {}
        self._retention_days = retention_days
        self._archived: Dict[str, DialogueContext] = {}

    def store(self, context: DialogueContext) -> None:
        """Store or update a dialogue context."""
        self._contexts[context.context_id] = context

    def retrieve(self, context_id: str) -> Optional[DialogueContext]:
        """Retrieve a dialogue context by ID."""
        return self._contexts.get(context_id)

    def delete(self, context_id: str) -> bool:
        """Delete a dialogue context."""
        if context_id in self._contexts:
            self._archived[context_id] = self._contexts.pop(context_id)
            return True
        return False

    def query_by_participant(self, participant_id: str) -> List[DialogueContext]:
        """Find all contexts for a given participant."""
        return [
            ctx for ctx in self._contexts.values()
            if ctx.participant_id == participant_id
        ]

    def query_by_platform(self, platform: str) -> List[DialogueContext]:
        """Find all contexts originating from a specific platform."""
        return [
            ctx for ctx in self._contexts.values()
            if ctx.origin_platform == platform
        ]

    def cleanup_expired(self) -> int:
        """Remove contexts older than retention period. Returns count removed."""
        now = datetime.now()
        cutoff = now - timedelta(days=self._retention_days)
        
        expired_ids = [
            ctx_id for ctx_id, ctx in self._contexts.items()
            if ctx.updated_at < cutoff
        ]
        
        for ctx_id in expired_ids:
            self.delete(ctx_id)
        
        return len(expired_ids)

    def list_contexts(self) -> List[DialogueContext]:
        """List all active contexts."""
        return list(self._contexts.values())
