"""Axioms and the gate: declare rules over actions and enforce them before execution.

>>> from aeon.axioms import axiom, enforce
>>> @axiom(on_violation="BLOCK")
... def no_destructive_tool_call(action):
...     return action.tool not in {"delete_file"} or action.approved
"""

from aeon.axioms import builtin
from aeon.axioms._gate import (
    AxiomRegistry,
    AxiomSpec,
    Gate,
    KillSwitch,
    SafeState,
    axiom,
    capture,
    default_gate,
    enforce,
    registry,
    set_default_gate,
)
from aeon.axioms._types import (
    ALERT,
    BLOCK,
    GO,
    LIMIT,
    Action,
    ActionBlocked,
    ActionLimited,
    AeonError,
    Decision,
    Finding,
    Level,
    Mode,
    SafeStateActive,
    Violation,
)

__all__ = [
    "ALERT",
    "BLOCK",
    "GO",
    "LIMIT",
    "Action",
    "ActionBlocked",
    "ActionLimited",
    "AeonError",
    "AxiomRegistry",
    "AxiomSpec",
    "Decision",
    "Finding",
    "Gate",
    "KillSwitch",
    "Level",
    "Mode",
    "SafeState",
    "SafeStateActive",
    "Violation",
    "axiom",
    "builtin",
    "capture",
    "default_gate",
    "enforce",
    "registry",
    "set_default_gate",
]
