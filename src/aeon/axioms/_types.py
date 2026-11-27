"""Value types of the decision path: actions, verdicts, violations and decisions."""

from __future__ import annotations

import enum
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from aeon._util import digest, new_id, utc_now_iso


class Level(enum.IntEnum):
    """Autonomy levels, ordered by severity.

    ``GO`` means no rule objected. ``ALERT`` records and never interferes. ``LIMIT``
    restricts (the action needs approval and does not run without it). ``BLOCK`` stops
    the action and moves the agent to its Safe State.
    """

    GO = 0
    ALERT = 1
    LIMIT = 2
    BLOCK = 3

    @classmethod
    def parse(cls, value: str | Level) -> Level:
        if isinstance(value, Level):
            return value
        try:
            return cls[value.strip().upper()]
        except KeyError:
            allowed = ", ".join(m.name for m in cls if m is not cls.GO)
            raise ValueError(f"unknown level {value!r}; expected one of {allowed}") from None


# Public aliases so `from aeon.axioms import ALERT, LIMIT, BLOCK` works.
GO = Level.GO
ALERT = Level.ALERT
LIMIT = Level.LIMIT
BLOCK = Level.BLOCK


class Mode(str, enum.Enum):
    """``shadow`` decides and records but never enforces. ``enforce`` applies the verdict."""

    SHADOW = "shadow"
    ENFORCE = "enforce"

    @classmethod
    def parse(cls, value: str | Mode) -> Mode:
        if isinstance(value, Mode):
            return value
        try:
            return cls(value.strip().lower())
        except ValueError:
            raise ValueError(f"unknown mode {value!r}; expected 'shadow' or 'enforce'") from None


@dataclass(frozen=True)
class Action:
    """One action an agent is about to take: a tool name plus its arguments.

    ``approved`` is set by a human or an approval hook. ``context`` carries anything an
    axiom may need (the user's request, the step number, the environment).
    """

    tool: str
    args: Mapping[str, Any] = field(default_factory=dict)
    agent: str = "default"
    approved: bool = False
    context: Mapping[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=new_id)

    def args_digest(self) -> str:
        return digest(dict(self.args))

    def with_approval(self, approved: bool = True) -> Action:
        return Action(self.tool, self.args, self.agent, approved, self.context, self.id)


@dataclass(frozen=True)
class Violation:
    """What an axiom returns to object to an action. ``level`` overrides the axiom default."""

    reason: str
    level: Level | None = None


@dataclass(frozen=True)
class Finding:
    """One axiom's objection, as recorded in a decision."""

    axiom: str
    level: Level
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"axiom": self.axiom, "level": self.level.name, "reason": self.reason}


@dataclass(frozen=True)
class Decision:
    """The gate's answer for one action.

    ``verdict`` is what the rules concluded. ``enforced`` says whether that verdict was
    applied (false in shadow mode). ``allowed`` says whether the action may run.
    """

    action: Action
    verdict: Level
    mode: Mode
    findings: tuple[Finding, ...]
    allowed: bool
    enforced: bool
    safe_state: bool
    gate_error: str | None = None
    decided_ns: int = 0
    ts: str = field(default_factory=utc_now_iso)
    id: str = field(default_factory=new_id)

    @property
    def reasons(self) -> list[str]:
        return [f.reason for f in self.findings]

    def to_record(self, *, include_args: bool = False) -> dict[str, Any]:
        """The audit form. Arguments are digested unless ``include_args`` is set."""
        rec: dict[str, Any] = {
            "decision_id": self.id,
            "action_id": self.action.id,
            "agent": self.action.agent,
            "tool": self.action.tool,
            "arg_keys": sorted(str(k) for k in self.action.args),
            "args_sha256": self.action.args_digest(),
            "approved": self.action.approved,
            "verdict": self.verdict.name,
            "mode": self.mode.value,
            "allowed": self.allowed,
            "enforced": self.enforced,
            "safe_state": self.safe_state,
            "findings": [f.to_dict() for f in self.findings],
            "decided_ns": self.decided_ns,
            "decided_at": self.ts,
        }
        if include_args:
            rec["args"] = dict(self.action.args)
        if self.gate_error:
            rec["gate_error"] = self.gate_error
        return rec


class AeonError(Exception):
    """Base class for errors raised by Æon."""


class ActionBlocked(AeonError):
    """Raised by an enforced executor when the gate blocks an action."""

    def __init__(self, decision: Decision) -> None:
        self.decision = decision
        why = "; ".join(decision.reasons) or decision.gate_error or "blocked"
        super().__init__(f"Æon blocked {decision.action.tool!r} ({decision.verdict.name}): {why}")


class ActionLimited(ActionBlocked):
    """Raised when a LIMIT verdict was not approved. The agent stays out of Safe State."""


class SafeStateActive(ActionBlocked):
    """Raised when an agent already in Safe State attempts another action."""
