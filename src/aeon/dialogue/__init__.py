"""
Dialogue Module: Conversation State Management.
Manages persistent dialogue contexts, message histories, and turn-taking semantics.
Architecture: Event-Sourced Conversation History.
"""

from aeon.dialogue.context import DialogueContext, Turn
from aeon.dialogue.archive import DialogueArchive

__all__ = ["DialogueContext", "Turn", "DialogueArchive"]
