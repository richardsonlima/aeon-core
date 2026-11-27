"""The gate: evaluates axioms before an action runs and applies the verdict.

The decision path (``Gate.decide``) is synchronous, uses only the stdlib, and never
waits on I/O. Audit records and metrics are handed to the observation path through a
non-blocking queue.
"""

from __future__ import annotations

import functools
import inspect
import threading
import time
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, cast, overload

from aeon._util import utc_now_iso
from aeon.axioms._types import (
    Action,
    ActionBlocked,
    ActionLimited,
    Decision,
    Finding,
    Level,
    Mode,
    SafeStateActive,
    Violation,
)

if TYPE_CHECKING:
    from aeon.baseline import Monitor

AxiomFn = Callable[[Action], Any]
Approver = Callable[[Decision], bool]
F = TypeVar("F", bound=Callable[..., Any])


class AuditSink(Protocol):
    """What the gate needs from an audit log. ``emit`` must not block."""

    def emit(self, type: str, data: Mapping[str, Any]) -> None: ...


@dataclass(frozen=True)
class AxiomSpec:
    """A registered axiom: the rule function plus its declared level and scope."""

    name: str
    fn: AxiomFn
    level: Level
    tools: frozenset[str] | None = None
    description: str = ""

    def applies_to(self, tool: str) -> bool:
        return self.tools is None or tool in self.tools

    def check(self, action: Action) -> Finding | None:
        """Run the rule. Returns a finding when it objects, ``None`` when it passes."""
        result = self.fn(action)
        if result is True or result is None:
            return None
        if result is False:
            return Finding(self.name, self.level, self.description or f"{self.name} returned False")
        if isinstance(result, Violation):
            return Finding(self.name, result.level or self.level, result.reason)
        if isinstance(result, str):
            return Finding(self.name, self.level, result)
        raise TypeError(
            f"axiom {self.name!r} returned {type(result).__name__}; "
            "expected bool, None, str or Violation"
        )


class AxiomRegistry:
    """An ordered, thread-safe collection of axioms."""

    def __init__(self, axioms: Iterable[AxiomSpec] = ()) -> None:
        self._lock = threading.Lock()
        self._axioms: dict[str, AxiomSpec] = {}
        for spec in axioms:
            self.add(spec)

    def add(self, spec: AxiomSpec) -> None:
        with self._lock:
            self._axioms[spec.name] = spec

    def remove(self, name: str) -> None:
        with self._lock:
            self._axioms.pop(name, None)

    def clear(self) -> None:
        with self._lock:
            self._axioms.clear()

    def snapshot(self) -> tuple[AxiomSpec, ...]:
        with self._lock:
            return tuple(self._axioms.values())

    def __len__(self) -> int:
        return len(self._axioms)

    def __iter__(self) -> Any:
        return iter(self.snapshot())


@dataclass
class SafeState:
    """Why and since when an agent is held in Safe State."""

    agent: str
    reason: str
    decision_id: str
    since: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, str]:
        return {
            "agent": self.agent,
            "reason": self.reason,
            "decision_id": self.decision_id,
            "since": self.since,
        }


class KillSwitch:
    """Operator stop. While engaged, every action of every agent is blocked, in any mode."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reason: str | None = None
        self._since: str | None = None

    @property
    def engaged(self) -> bool:
        return self._reason is not None

    @property
    def reason(self) -> str | None:
        return self._reason

    def engage(self, reason: str = "kill-switch engaged") -> None:
        with self._lock:
            self._reason = reason or "kill-switch engaged"
            self._since = utc_now_iso()

    def release(self) -> None:
        with self._lock:
            self._reason = None
            self._since = None

    def to_dict(self) -> dict[str, Any]:
        return {"engaged": self.engaged, "reason": self._reason, "since": self._since}


class Gate:
    """Evaluates axioms for each action and applies the verdict according to the mode.

    Fail-safe rule: if an axiom or the gate itself raises, the verdict is BLOCK. In
    enforce mode the action does not run; in shadow mode it runs and the error is logged.
    """

    def __init__(
        self,
        axioms: AxiomRegistry | Iterable[AxiomSpec] | None = None,
        *,
        mode: Mode | str = Mode.SHADOW,
        audit: AuditSink | None = None,
        monitor: Monitor | None = None,
        approver: Approver | None = None,
        include_args: bool = False,
    ) -> None:
        if isinstance(axioms, AxiomRegistry):
            self.axioms = axioms
        else:
            self.axioms = AxiomRegistry(axioms or ())
        self.mode = Mode.parse(mode)
        self.audit = audit
        self.monitor = monitor
        self.approver = approver
        self.include_args = include_args
        self.kill_switch = KillSwitch()
        self._lock = threading.Lock()
        self._safe: dict[str, SafeState] = {}
        self._subscribers: list[Callable[[Decision], None]] = []
        self._pending_safe = threading.local()
        self.counters: dict[str, int] = {
            "decisions": 0,
            "allowed": 0,
            "denied": 0,
            "gate_errors": 0,
            "subscriber_errors": 0,
        }

    # -- configuration -----------------------------------------------------------------

    def set_mode(self, mode: Mode | str) -> None:
        old = self.mode
        self.mode = Mode.parse(mode)
        self._emit("mode", {"from": old.value, "to": self.mode.value})

    def engage_kill_switch(self, reason: str = "kill-switch engaged") -> None:
        self.kill_switch.engage(reason)
        self._emit("kill_switch", {"engaged": True, "reason": reason})

    def release_kill_switch(self) -> None:
        self.kill_switch.release()
        self._emit("kill_switch", {"engaged": False})

    def subscribe(self, callback: Callable[[Decision], None]) -> Callable[[], None]:
        """Call ``callback`` after every decision. Returns an unsubscribe function."""
        with self._lock:
            self._subscribers.append(callback)

        def unsubscribe() -> None:
            with self._lock:
                if callback in self._subscribers:
                    self._subscribers.remove(callback)

        return unsubscribe

    # -- safe state --------------------------------------------------------------------

    def safe_state(self, agent: str = "default") -> SafeState | None:
        return self._safe.get(agent)

    def safe_states(self) -> dict[str, SafeState]:
        with self._lock:
            return dict(self._safe)

    def reset(self, agent: str = "default") -> bool:
        """Release ``agent`` from Safe State. Returns whether it was held."""
        with self._lock:
            held = self._safe.pop(agent, None)
        if held is not None:
            self._emit("safe_state", {"agent": agent, "entered": False})
            if self.monitor is not None:
                self.monitor.reset_accumulated(agent)
        return held is not None

    # -- decision path -----------------------------------------------------------------

    def decide(self, action: Action) -> Decision:
        """Decide whether ``action`` may run. Never raises."""
        t0 = time.perf_counter_ns()
        mode = self.mode
        try:
            decision = self._decide(action, mode, t0)
        except Exception as exc:  # the gate itself failed: fail closed in enforce mode
            self.counters["gate_errors"] += 1
            enforce = mode is Mode.ENFORCE
            decision = Decision(
                action=action,
                verdict=Level.BLOCK,
                mode=mode,
                findings=(Finding("gate", Level.BLOCK, f"gate error: {exc!r}"),),
                allowed=not enforce,
                enforced=enforce,
                safe_state=False,
                gate_error=repr(exc),
                decided_ns=time.perf_counter_ns() - t0,
            )
        self._publish(decision)
        entered: SafeState | None = getattr(self._pending_safe, "entered", None)
        if entered is not None:
            self._pending_safe.entered = None
            self._emit("safe_state", {"entered": True, **entered.to_dict()})
        return decision

    def _decide(self, action: Action, mode: Mode, t0: int) -> Decision:
        findings: list[Finding] = []
        gate_error: str | None = None

        if self.kill_switch.engaged:
            findings.append(Finding("kill-switch", Level.BLOCK, self.kill_switch.reason or ""))
        held = self._safe.get(action.agent)
        if held is not None and mode is Mode.ENFORCE:
            findings.append(
                Finding("safe-state", Level.BLOCK, f"agent in Safe State: {held.reason}")
            )

        for spec in self.axioms.snapshot():
            if not spec.applies_to(action.tool):
                continue
            try:
                finding = spec.check(action)
            except Exception as exc:
                self.counters["gate_errors"] += 1
                gate_error = gate_error or f"{spec.name}: {exc!r}"
                finding = Finding(spec.name, Level.BLOCK, f"axiom raised {exc!r}")
            if finding is not None:
                findings.append(finding)

        if self.monitor is not None:
            budget_finding = self.monitor.finding(action.agent)
            if budget_finding is not None:
                findings.append(budget_finding)

        verdict = max((f.level for f in findings), default=Level.GO)
        killed = self.kill_switch.engaged
        enforced = mode is Mode.ENFORCE or killed
        allowed = True
        entered_safe = False
        provisional = Decision(
            action, verdict, mode, tuple(findings), True, enforced, False, gate_error
        )

        if enforced:
            if verdict is Level.BLOCK:
                allowed = False
                entered_safe = True
            elif verdict is Level.LIMIT:
                allowed = action.approved or self._approve(provisional)

        newly_safe: SafeState | None = None
        if entered_safe:
            reason = "; ".join(f.reason for f in findings if f.level is Level.BLOCK)
            with self._lock:
                if action.agent not in self._safe:
                    newly_safe = SafeState(action.agent, reason, provisional.id)
                    self._safe[action.agent] = newly_safe
        self._pending_safe.entered = newly_safe

        return Decision(
            action=action,
            verdict=verdict,
            mode=mode,
            findings=tuple(findings),
            allowed=allowed,
            enforced=enforced,
            safe_state=action.agent in self._safe,
            gate_error=gate_error,
            decided_ns=time.perf_counter_ns() - t0,
            ts=provisional.ts,
            id=provisional.id,
        )

    def _approve(self, decision: Decision) -> bool:
        if self.approver is None:
            return False
        try:
            return bool(self.approver(decision))
        except Exception:
            self.counters["gate_errors"] += 1
            return False  # an approval hook that fails does not approve

    def _publish(self, decision: Decision) -> None:
        with self._lock:
            self.counters["decisions"] += 1
            self.counters["allowed" if decision.allowed else "denied"] += 1
        self._emit("decision", decision.to_record(include_args=self.include_args))
        for cb in tuple(self._subscribers):
            try:
                cb(decision)
            except Exception:
                self.counters["subscriber_errors"] += 1

    def _emit(self, type: str, data: Mapping[str, Any]) -> None:
        if self.audit is None:
            return
        try:
            self.audit.emit(type, data)
        except Exception:  # the observation path must never break a decision
            self.counters["gate_errors"] += 1

    # -- observation path ---------------------------------------------------------------

    def observe(
        self,
        action: Action,
        *,
        latency_ms: float,
        error: BaseException | None = None,
        tokens: int | None = None,
        cost: float | None = None,
    ) -> None:
        """Record the outcome of an action that ran. Feeds the baseline and the audit log."""
        if self.monitor is not None:
            self.monitor.record(
                action, latency_ms=latency_ms, error=error is not None, tokens=tokens, cost=cost
            )
        data: dict[str, Any] = {
            "action_id": action.id,
            "agent": action.agent,
            "tool": action.tool,
            "latency_ms": round(latency_ms, 4),
            "ok": error is None,
        }
        if error is not None:
            data["error"] = type(error).__name__
        if tokens is not None:
            data["tokens"] = tokens
        if cost is not None:
            data["cost"] = cost
        self._emit("result", data)

    def status(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "axioms": [s.name for s in self.axioms.snapshot()],
            "kill_switch": self.kill_switch.to_dict(),
            "safe_states": {k: v.to_dict() for k, v in self.safe_states().items()},
            "counters": dict(self.counters),
            "budget": self.monitor.status() if self.monitor is not None else None,
        }

    # -- wrapping ----------------------------------------------------------------------

    def enforce(self, executor: F, **kwargs: Any) -> F:
        return enforce(executor, gate=self, **kwargs)


# -- module-level registry and default gate --------------------------------------------

_registry = AxiomRegistry()
_default_gate: Gate | None = None
_default_lock = threading.Lock()


def registry() -> AxiomRegistry:
    """The registry that ``@axiom`` writes to when no gate is given."""
    return _registry


def _current_registry() -> AxiomRegistry:
    return _registry


def default_gate() -> Gate:
    """The process-wide gate, built from ``aeon.toml`` and ``AEON_*`` variables on first use."""
    global _default_gate
    with _default_lock:
        if _default_gate is None:
            from aeon.config import build_gate, load_config

            _default_gate = build_gate(load_config(), axioms=_registry)
        return _default_gate


def set_default_gate(gate: Gate | None) -> None:
    """Replace the process-wide gate (``None`` rebuilds it from config on next use)."""
    global _default_gate
    with _default_lock:
        _default_gate = gate


@overload
def axiom(fn: AxiomFn, /) -> AxiomFn: ...
@overload
def axiom(
    *,
    on_violation: str | Level = ...,
    name: str | None = ...,
    tools: Iterable[str] | None = ...,
    description: str = ...,
    gate: Gate | None = ...,
) -> Callable[[AxiomFn], AxiomFn]: ...


def axiom(
    fn: AxiomFn | None = None,
    /,
    *,
    on_violation: str | Level = Level.BLOCK,
    name: str | None = None,
    tools: Iterable[str] | None = None,
    description: str = "",
    gate: Gate | None = None,
) -> AxiomFn | Callable[[AxiomFn], AxiomFn]:
    """Declare a rule over an action.

    The function receives an :class:`Action` and returns ``True`` (or ``None``) to pass,
    ``False`` or a reason string to object at ``on_violation`` level, or a
    :class:`Violation` to choose the level per call. ``tools`` limits the rule to those
    tool names. The function is registered and returned unchanged, so it stays testable.
    """
    level = Level.parse(on_violation)
    if level is Level.GO:
        raise ValueError("on_violation must be ALERT, LIMIT or BLOCK")

    def register(f: AxiomFn) -> AxiomFn:
        spec = AxiomSpec(
            name=name or str(getattr(f, "__name__", "axiom")),
            fn=f,
            level=level,
            tools=frozenset(tools) if tools is not None else None,
            description=description or (inspect.getdoc(f) or "").split("\n", 1)[0],
        )
        (gate.axioms if gate is not None else _current_registry()).add(spec)
        f.__aeon_axiom__ = spec  # type: ignore[attr-defined]
        return f

    return register(fn) if fn is not None else register


# -- enforce ---------------------------------------------------------------------------

_EXECUTOR_TOOL_PARAMS = {"tool", "tool_name", "name"}
_EXECUTOR_ARGS_PARAMS = {"args", "arguments", "input", "tool_input", "params", "parameters"}


ActionBuilder = Callable[[tuple[Any, ...], dict[str, Any]], Action]


def _action_builder(
    executor: Callable[..., Any], tool: str | None, agent: str, context: Mapping[str, Any]
) -> ActionBuilder:
    """Pick how to read an Action from the executor's call arguments, once, at wrap time.

    - first parameter named ``action``: the caller passes an :class:`Action`;
    - first two parameters named like ``(tool, args)``: a generic tool executor;
    - anything else: the function itself is the tool, its bound arguments are the args.
    """
    try:
        sig: inspect.Signature | None = inspect.signature(executor)
        params = [
            p
            for p in sig.parameters.values()  # type: ignore[union-attr]
            if p.name not in {"self", "cls"}
        ]
    except (TypeError, ValueError):
        sig, params = None, []
    names = [p.name for p in params]

    if tool is None and names[:1] == ["action"]:

        def from_action(a: tuple[Any, ...], kw: dict[str, Any]) -> Action:
            act = a[0] if a else kw.get("action")
            if not isinstance(act, Action):
                raise TypeError("executor expects an aeon Action as its first argument")
            return act

        return from_action

    if (
        tool is None
        and len(names) >= 2
        and names[0] in _EXECUTOR_TOOL_PARAMS
        and names[1] in _EXECUTOR_ARGS_PARAMS
    ):
        tool_param, args_param = names[0], names[1]

        def from_executor(a: tuple[Any, ...], kw: dict[str, Any]) -> Action:
            t = a[0] if a else kw[tool_param]
            raw = a[1] if len(a) > 1 else kw.get(args_param, {})
            args = dict(raw) if isinstance(raw, Mapping) else {"value": raw}
            return Action(tool=str(t), args=args, agent=agent, context=context)

        return from_executor

    tool_name = tool or str(getattr(executor, "__name__", "tool"))

    def from_function(a: tuple[Any, ...], kw: dict[str, Any]) -> Action:
        if sig is not None:
            try:
                bound = sig.bind_partial(*a, **kw)
                args = {k: v for k, v in bound.arguments.items() if k not in {"self", "cls"}}
            except TypeError:
                args = {"args": list(a), **kw}
        else:
            args = {"args": list(a), **kw}
        return Action(tool=tool_name, args=args, agent=agent, context=context)

    return from_function


def _deny(decision: Decision) -> ActionBlocked:
    findings = {f.axiom for f in decision.findings}
    if decision.verdict is Level.LIMIT:
        return ActionLimited(decision)
    if "safe-state" in findings and len(findings) == 1:
        return SafeStateActive(decision)
    return ActionBlocked(decision)


@overload
def enforce(
    executor: F,
    /,
    *,
    gate: Gate | None = ...,
    agent: str = ...,
    tool: str | None = ...,
    to_action: ActionBuilder | None = ...,
    context: Mapping[str, Any] | None = ...,
) -> F: ...
@overload
def enforce(
    executor: None = None,
    /,
    *,
    gate: Gate | None = ...,
    agent: str = ...,
    tool: str | None = ...,
    to_action: ActionBuilder | None = ...,
    context: Mapping[str, Any] | None = ...,
) -> Callable[[F], F]: ...


def enforce(
    executor: F | None = None,
    /,
    *,
    gate: Gate | None = None,
    agent: str = "default",
    tool: str | None = None,
    to_action: ActionBuilder | None = None,
    context: Mapping[str, Any] | None = None,
) -> F | Callable[[F], F]:
    """Wrap an executor so every call is checked by the gate before it runs.

    Works on sync and async callables, directly or as a decorator. A denied call raises
    :class:`ActionBlocked` (or its subclasses :class:`ActionLimited`,
    :class:`SafeStateActive`) and the executor is not called.
    """

    def wrap(fn: F) -> F:
        ctx = dict(context or {})
        build = to_action or _action_builder(fn, tool, agent, ctx)

        def gate_for_call() -> Gate:
            return gate if gate is not None else default_gate()

        def admit(a: tuple[Any, ...], kw: dict[str, Any]) -> tuple[Gate, Action]:
            g = gate_for_call()
            action = build(a, kw)
            decision = g.decide(action)
            if not decision.allowed:
                raise _deny(decision)
            return g, action

        if inspect.iscoroutinefunction(fn):
            async_fn = cast(Callable[..., Awaitable[Any]], fn)

            @functools.wraps(fn)
            async def async_wrapper(*a: Any, **kw: Any) -> Any:
                g, action = admit(a, kw)
                t0 = time.perf_counter()
                try:
                    result = await async_fn(*a, **kw)
                except BaseException as exc:
                    g.observe(action, latency_ms=(time.perf_counter() - t0) * 1e3, error=exc)
                    raise
                g.observe(action, latency_ms=(time.perf_counter() - t0) * 1e3)
                return result

            async_wrapper.__aeon_enforced__ = True  # type: ignore[attr-defined]
            return cast(F, async_wrapper)

        @functools.wraps(fn)
        def wrapper(*a: Any, **kw: Any) -> Any:
            g, action = admit(a, kw)
            t0 = time.perf_counter()
            try:
                result = fn(*a, **kw)
            except BaseException as exc:
                g.observe(action, latency_ms=(time.perf_counter() - t0) * 1e3, error=exc)
                raise
            g.observe(action, latency_ms=(time.perf_counter() - t0) * 1e3)
            return result

        wrapper.__aeon_enforced__ = True  # type: ignore[attr-defined]
        return cast(F, wrapper)

    return wrap(executor) if executor is not None else wrap


class capture:
    """Context manager: redirect module-level ``@axiom`` registrations into a new registry.

    Used to load an axiom file in isolation (``aeon axioms check``).
    """

    def __init__(self) -> None:
        self.registry = AxiomRegistry()
        self._saved: AxiomRegistry | None = None

    def __enter__(self) -> AxiomRegistry:
        global _registry
        self._saved = _registry
        _registry = self.registry
        return self.registry

    def __exit__(self, *exc: object) -> None:
        global _registry
        assert self._saved is not None
        _registry = self._saved
