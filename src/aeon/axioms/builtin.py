"""Ready-made axiom factories. Each returns an :class:`AxiomSpec` to pass to a Gate.

They are deliberately simple and syntactic: they look at tool names and argument
values, never at the meaning of free text (see docs/known-limits.md).
"""

from __future__ import annotations

import re
import threading
import time
from collections import deque
from collections.abc import Iterable

from aeon.axioms._gate import AxiomSpec
from aeon.axioms._types import Action, Level, Violation


def deny_tools(
    tools: Iterable[str],
    *,
    unless_approved: bool = True,
    level: Level | str = Level.BLOCK,
    name: str = "deny_tools",
) -> AxiomSpec:
    """Object to the listed tools. With ``unless_approved``, an approved action passes."""
    denied = frozenset(tools)

    def rule(action: Action) -> bool | str:
        if action.tool not in denied:
            return True
        if unless_approved and action.approved:
            return True
        return f"tool {action.tool!r} is on the deny list"

    return AxiomSpec(name, rule, Level.parse(level), description="deny listed tools")


def allow_tools(
    tools: Iterable[str], *, level: Level | str = Level.BLOCK, name: str = "allow_tools"
) -> AxiomSpec:
    """Object to any tool that is not on the allow list."""
    allowed = frozenset(tools)

    def rule(action: Action) -> bool | str:
        return action.tool in allowed or f"tool {action.tool!r} is not on the allow list"

    return AxiomSpec(name, rule, Level.parse(level), description="allow listed tools only")


def rate_limit(
    max_calls: int,
    per_seconds: float,
    *,
    tools: Iterable[str] | None = None,
    level: Level | str = Level.LIMIT,
    name: str = "rate_limit",
    clock: object = None,
) -> AxiomSpec:
    """Object once an agent exceeds ``max_calls`` within a sliding window.

    Counts decisions, not executions, so a denied call still counts. ``clock`` is a
    zero-argument callable returning seconds (monotonic by default), for tests.
    """
    now = clock if callable(clock) else time.monotonic
    windows: dict[str, deque[float]] = {}
    lock = threading.Lock()

    def rule(action: Action) -> bool | Violation:
        t = float(now())
        with lock:
            q = windows.setdefault(action.agent, deque())
            while q and t - q[0] > per_seconds:
                q.popleft()
            q.append(t)
            n = len(q)
        if n > max_calls:
            return Violation(f"{n} calls in {per_seconds:g}s exceeds {max_calls}")
        return True

    return AxiomSpec(
        name,
        rule,
        Level.parse(level),
        tools=frozenset(tools) if tools is not None else None,
        description="rate limit per agent",
    )


def deny_arg_pattern(
    pattern: str,
    *,
    args: Iterable[str] | None = None,
    tools: Iterable[str] | None = None,
    level: Level | str = Level.BLOCK,
    name: str = "deny_arg_pattern",
) -> AxiomSpec:
    """Object when a string argument matches ``pattern`` (a Python regex)."""
    rx = re.compile(pattern)
    only = frozenset(args) if args is not None else None

    def rule(action: Action) -> bool | str:
        for key, value in action.args.items():
            if only is not None and key not in only:
                continue
            if isinstance(value, str) and rx.search(value):
                return f"argument {key!r} matches {pattern!r}"
        return True

    return AxiomSpec(
        name,
        rule,
        Level.parse(level),
        tools=frozenset(tools) if tools is not None else None,
        description=f"deny arguments matching {pattern}",
    )


def require_approval(tools: Iterable[str], *, name: str = "require_approval") -> AxiomSpec:
    """LIMIT the listed tools: they run only when the action is approved."""
    needed = frozenset(tools)

    def rule(action: Action) -> bool | str:
        return action.approved or f"tool {action.tool!r} requires approval"

    return AxiomSpec(name, rule, Level.LIMIT, tools=needed, description="require approval")


__all__ = ["allow_tools", "deny_arg_pattern", "deny_tools", "rate_limit", "require_approval"]
