from __future__ import annotations

import asyncio
import threading
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from aeon.axioms import (
    ALERT,
    BLOCK,
    LIMIT,
    Action,
    ActionBlocked,
    ActionLimited,
    Gate,
    Level,
    SafeStateActive,
    Violation,
    axiom,
    enforce,
)
from aeon.axioms.builtin import (
    allow_tools,
    deny_arg_pattern,
    deny_tools,
    rate_limit,
    require_approval,
)
from tests.conftest import ListSink


def test_go_when_no_axiom_objects(gate: Gate) -> None:
    d = gate.decide(Action("ls"))
    assert d.verdict is Level.GO and d.allowed and not d.safe_state


def test_block_stops_action_and_enters_safe_state(gate: Gate, sink: ListSink) -> None:
    @axiom(on_violation="BLOCK", gate=gate)
    def no_rm(action: Action) -> bool:
        return action.tool != "rm"

    d = gate.decide(Action("rm", {"path": "/"}))
    assert d.verdict is BLOCK and not d.allowed and d.safe_state
    assert gate.safe_state("default") is not None
    # every later action of the same agent is blocked
    d2 = gate.decide(Action("ls"))
    assert not d2.allowed and d2.findings[0].axiom == "safe-state"
    # other agents are not affected
    assert gate.decide(Action("ls", agent="other")).allowed
    assert [e["entered"] for e in sink.of("safe_state")] == [True]
    assert gate.reset("default") is True
    assert gate.decide(Action("ls")).allowed


def test_alert_never_interferes(gate: Gate) -> None:
    gate.axioms.add(deny_tools(["curl"], level="ALERT", unless_approved=False))
    d = gate.decide(Action("curl"))
    assert d.verdict is ALERT and d.allowed and not d.safe_state


def test_limit_requires_approval(gate: Gate) -> None:
    gate.axioms.add(require_approval(["deploy"]))
    d = gate.decide(Action("deploy"))
    assert d.verdict is LIMIT and not d.allowed and not d.safe_state
    assert gate.decide(Action("deploy", approved=True)).allowed


def test_limit_approver_hook(sink: ListSink) -> None:
    seen: list[str] = []

    def approver(decision: Any) -> bool:
        seen.append(decision.action.tool)
        return decision.action.args.get("env") == "staging"

    g = Gate([require_approval(["deploy"])], mode="enforce", approver=approver, audit=sink)
    assert g.decide(Action("deploy", {"env": "staging"})).allowed
    assert not g.decide(Action("deploy", {"env": "prod"})).allowed
    assert seen == ["deploy", "deploy"]


def test_approver_that_raises_does_not_approve() -> None:
    def boom(_: Any) -> bool:
        raise RuntimeError("x")

    g = Gate([require_approval(["deploy"])], mode="enforce", approver=boom)
    assert not g.decide(Action("deploy")).allowed
    assert g.counters["gate_errors"] == 1


def test_violation_overrides_level(gate: Gate) -> None:
    @axiom(on_violation="BLOCK", gate=gate)
    def soft(action: Action) -> Violation | bool:
        return Violation("just a heads-up", level=ALERT) if action.tool == "x" else True

    d = gate.decide(Action("x"))
    assert d.verdict is ALERT and d.reasons == ["just a heads-up"]


def test_string_return_is_a_reason(gate: Gate) -> None:
    gate.axioms.add(deny_tools(["rm"]))
    assert gate.decide(Action("rm")).reasons == ["tool 'rm' is on the deny list"]


def test_tools_scope(gate: Gate) -> None:
    @axiom(gate=gate, tools=["rm"])
    def never(action: Action) -> bool:
        return False

    assert gate.decide(Action("ls")).allowed
    assert not gate.decide(Action("rm")).allowed


def test_invalid_return_type_fails_closed(gate: Gate) -> None:
    @axiom(gate=gate)
    def weird(action: Action) -> int:
        return 3

    d = gate.decide(Action("ls"))
    assert d.verdict is BLOCK and not d.allowed and d.gate_error


def test_axiom_raising_blocks_in_enforce() -> None:
    g = Gate(mode="enforce")

    @axiom(gate=g)
    def broken(action: Action) -> bool:
        raise ValueError("bug")

    d = g.decide(Action("ls"))
    assert d.verdict is BLOCK and not d.allowed and d.enforced
    assert "bug" in (d.gate_error or "")


def test_axiom_raising_allows_and_logs_in_shadow(sink: ListSink) -> None:
    g = Gate(mode="shadow", audit=sink)

    @axiom(gate=g)
    def broken(action: Action) -> bool:
        raise ValueError("bug")

    d = g.decide(Action("ls"))
    assert d.verdict is BLOCK and d.allowed and not d.enforced and not d.safe_state
    rec = sink.of("decision")[0]
    assert rec["verdict"] == "BLOCK" and rec["allowed"] is True and "gate_error" in rec


def test_gate_internal_error_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    for mode, allowed in (("enforce", False), ("shadow", True)):
        g = Gate(mode=mode)

        def explode(*a: Any) -> Any:
            raise RuntimeError("internal")

        monkeypatch.setattr(g, "_decide", explode)
        d = g.decide(Action("ls"))
        assert d.verdict is BLOCK and d.allowed is allowed and d.gate_error


def test_shadow_never_enforces(sink: ListSink) -> None:
    g = Gate([deny_tools(["rm"])], mode="shadow", audit=sink)
    d = g.decide(Action("rm"))
    assert d.verdict is BLOCK and d.allowed and not d.enforced
    assert g.safe_states() == {}


def test_new_gate_defaults_to_shadow() -> None:
    assert Gate().mode.value == "shadow"


def test_kill_switch_blocks_everything_even_in_shadow(sink: ListSink) -> None:
    g = Gate(mode="shadow", audit=sink)
    g.engage_kill_switch("incident 42")
    d = g.decide(Action("ls", agent="a"))
    assert not d.allowed and d.enforced and d.verdict is BLOCK
    assert d.findings[0].axiom == "kill-switch" and "incident 42" in d.reasons[0]
    g.release_kill_switch()
    g.reset("a")
    assert g.decide(Action("ls", agent="a")).allowed
    assert [e["engaged"] for e in sink.of("kill_switch")] == [True, False]


def test_mode_switch_is_audited(gate: Gate, sink: ListSink) -> None:
    gate.set_mode("shadow")
    assert sink.of("mode") == [{"from": "enforce", "to": "shadow"}]
    with pytest.raises(ValueError, match="unknown mode"):
        gate.set_mode("yolo")


def test_audit_sink_failure_does_not_break_decisions() -> None:
    class Broken:
        def emit(self, *a: Any) -> None:
            raise OSError("disk gone")

    g = Gate([deny_tools(["rm"])], mode="enforce", audit=Broken())
    assert g.decide(Action("ls")).allowed
    assert not g.decide(Action("rm", agent="b")).allowed
    assert g.counters["gate_errors"] >= 2


def test_subscriber_errors_are_counted(gate: Gate) -> None:
    got: list[str] = []
    gate.subscribe(lambda d: got.append(d.action.tool))
    gate.subscribe(lambda d: 1 / 0)
    gate.decide(Action("ls"))
    assert got == ["ls"] and gate.counters["subscriber_errors"] == 1


def test_records_digest_args_by_default(gate: Gate, sink: ListSink) -> None:
    gate.decide(Action("login", {"password": "hunter2"}))
    rec = sink.of("decision")[0]
    assert "args" not in rec and rec["arg_keys"] == ["password"]
    assert "hunter2" not in str(rec)
    g2 = Gate(audit=sink, include_args=True)
    g2.decide(Action("x", {"a": 1}))
    assert sink.of("decision")[-1]["args"] == {"a": 1}


# -- enforce ------------------------------------------------------------------------------


def test_enforce_function_tool(gate: Gate) -> None:
    calls: list[str] = []
    gate.axioms.add(deny_arg_pattern(r"^/$", args=["path"]))

    @enforce(gate=gate)
    def delete(path: str, recursive: bool = False) -> str:
        calls.append(path)
        return "ok"

    assert delete("/tmp/x") == "ok"
    with pytest.raises(ActionBlocked) as ei:
        delete(path="/")
    assert ei.value.decision.action.args == {"path": "/"}
    assert calls == ["/tmp/x"]


def test_enforce_generic_executor(gate: Gate, sink: ListSink) -> None:
    gate.axioms.add(deny_tools(["rm"]))

    def executor(tool_name: str, arguments: dict[str, Any]) -> str:
        return f"{tool_name}:{arguments}"

    run = enforce(executor, gate=gate, agent="bot")
    assert run("ls", {"p": 1}) == "ls:{'p': 1}"
    with pytest.raises(ActionBlocked):
        run("rm", {"p": "/"})
    assert sink.of("decision")[0]["agent"] == "bot"
    assert sink.of("result")[0]["tool"] == "ls"


def test_enforce_action_executor(gate: Gate) -> None:
    @axiom(gate=gate)
    def no_destructive(action: Action) -> bool:
        return action.tool not in {"rm"} or action.approved

    @enforce(gate=gate)
    def execute(action: Action) -> str:
        return action.tool

    assert execute(Action("rm", approved=True)) == "rm"
    with pytest.raises(ActionBlocked):
        execute(Action("rm"))
    with pytest.raises(TypeError):
        execute("rm")


def test_enforce_exception_types(gate: Gate) -> None:
    gate.axioms.add(require_approval(["deploy"]))
    gate.axioms.add(deny_tools(["rm"]))
    run = enforce(lambda tool, args: "ok", gate=gate)
    with pytest.raises(ActionLimited):
        run("deploy", {})
    assert gate.safe_states() == {}
    with pytest.raises(ActionBlocked) as ei:
        run("rm", {})
    assert not isinstance(ei.value, SafeStateActive)
    with pytest.raises(SafeStateActive):
        run("ls", {})


def test_enforce_observes_errors_and_reraises(gate: Gate, sink: ListSink) -> None:
    @enforce(gate=gate)
    def flaky() -> None:
        raise ConnectionError("down")

    with pytest.raises(ConnectionError):
        flaky()
    res = sink.of("result")[0]
    assert res["ok"] is False and res["error"] == "ConnectionError"


def test_enforce_async(gate: Gate) -> None:
    gate.axioms.add(deny_tools(["fetch_secret"]))

    @enforce(gate=gate)
    async def fetch(url: str) -> str:
        await asyncio.sleep(0)
        return url

    @enforce(gate=gate, tool="fetch_secret")
    async def secret() -> str:
        return "s"

    assert asyncio.run(fetch("u")) == "u"
    with pytest.raises(ActionBlocked):
        asyncio.run(secret())


def test_enforce_uses_default_gate_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AEON_MODE", "enforce")

    @axiom(on_violation="BLOCK")
    def no_destructive_tool_call(action: Action) -> bool:
        return action.tool not in {"drop_table"} or action.approved

    @enforce
    def drop_table(name: str) -> str:
        return name

    with pytest.raises(ActionBlocked):
        drop_table("users")


def test_enforce_preserves_metadata(gate: Gate) -> None:
    def tool(x: int) -> int:
        """Doc."""
        return x

    wrapped = enforce(tool, gate=gate)
    assert wrapped.__name__ == "tool" and wrapped.__doc__ == "Doc."
    assert wrapped.__wrapped__ is tool  # type: ignore[attr-defined]


def test_axiom_decorator_validation() -> None:
    with pytest.raises(ValueError):
        axiom(on_violation="GO")
    with pytest.raises(ValueError):
        axiom(on_violation="NOPE")


def test_bare_axiom_decorator_registers_and_returns_function() -> None:
    from aeon.axioms import registry

    @axiom
    def plain(action: Action) -> bool:
        """Plain rule."""
        return True

    assert plain(Action("x")) is True
    spec = registry().snapshot()[-1]
    assert spec.name == "plain" and spec.level is BLOCK and spec.description == "Plain rule."


# -- builtin axioms -----------------------------------------------------------------------


def test_allow_tools() -> None:
    g = Gate([allow_tools(["ls"])], mode="enforce")
    assert g.decide(Action("ls")).allowed
    assert not g.decide(Action("rm")).allowed


def test_rate_limit_sliding_window() -> None:
    t = [0.0]
    g = Gate([rate_limit(2, 1.0, clock=lambda: t[0])], mode="enforce")
    assert g.decide(Action("x")).allowed
    assert g.decide(Action("x")).allowed
    d = g.decide(Action("x"))
    assert d.verdict is LIMIT and not d.allowed
    t[0] = 5.0
    assert g.decide(Action("x")).allowed


# -- concurrency and properties -----------------------------------------------------------


def test_concurrent_decisions_are_consistent(sink: ListSink) -> None:
    g = Gate([deny_tools(["rm"])], mode="enforce", audit=sink)
    results: list[bool] = []
    lock = threading.Lock()

    def worker(i: int) -> None:
        for j in range(200):
            tool = "rm" if (i == 3 and j == 100) else "ls"
            d = g.decide(Action(tool, {"j": j}, agent=f"a{i}"))
            with lock:
                results.append(d.allowed)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert g.counters["decisions"] == 1600 == len(results)
    assert set(g.safe_states()) == {"a3"}
    # a3: 100 allowed, then the block, then 99 safe-state blocks
    assert results.count(False) == 100
    assert len(sink.of("decision")) == 1600


levels = st.sampled_from([ALERT, LIMIT, BLOCK])


@given(
    st.lists(st.tuples(levels, st.booleans()), max_size=8),
    st.booleans(),
    st.sampled_from(["shadow", "enforce"]),
)
def test_verdict_is_max_of_objections(
    rules: list[tuple[Level, bool]], approved: bool, mode: str
) -> None:
    g = Gate(mode=mode)
    for i, (level, objects) in enumerate(rules):
        g.axioms.add(
            __import__("aeon.axioms", fromlist=["AxiomSpec"]).AxiomSpec(
                f"r{i}", (lambda o: lambda a: not o)(objects), level
            )
        )
    d = g.decide(Action("t", approved=approved))
    expected = max((lv for lv, o in rules if o), default=Level.GO)
    assert d.verdict is expected
    if mode == "shadow":
        assert d.allowed
    else:
        should = expected <= ALERT or (expected is LIMIT and approved)
        assert d.allowed is should
        assert d.safe_state is (expected is BLOCK)
