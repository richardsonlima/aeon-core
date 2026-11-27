"""Æon Core: gate the actions of LLM agents and check that they fail safe.

Inspired by the MECADE framework for chaos engineering; an independent project.
"""

import logging

from aeon._version import __version__
from aeon.axioms import (
    ALERT,
    BLOCK,
    LIMIT,
    Action,
    ActionBlocked,
    ActionLimited,
    Decision,
    Gate,
    Level,
    Mode,
    SafeStateActive,
    Violation,
    axiom,
    default_gate,
    enforce,
)
from aeon.baseline import Budget, ChaosBudget, Monitor

# A library only creates loggers; the application decides where logs go.
logging.getLogger("aeon").addHandler(logging.NullHandler())

__all__ = [
    "ALERT",
    "BLOCK",
    "LIMIT",
    "Action",
    "ActionBlocked",
    "ActionLimited",
    "Budget",
    "ChaosBudget",
    "Decision",
    "Gate",
    "Level",
    "Mode",
    "Monitor",
    "SafeStateActive",
    "Violation",
    "__version__",
    "axiom",
    "default_gate",
    "enforce",
]
