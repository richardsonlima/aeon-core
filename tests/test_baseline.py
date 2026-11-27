from __future__ import annotations

import random

import pytest

from aeon.axioms import Action, Gate, Level
from aeon.baseline import Baseline, Budget, ChaosBudget, Monitor, js_divergence, p99


def feed(
    m: Monitor,
    n: int,
    *,
    rng: random.Random,
    latency: float = 10.0,
    err: float = 0.0,
    tools: tuple[str, ...] = ("a", "b"),
    agent: str = "x",
) -> list[float]:
    scores = []
    for _i in range(n):
        t = rng.choice(tools)
        scores.append(
            m.record(
                Action(t, {"i": rng.random()}, agent=agent),
                latency_ms=max(0.1, rng.gauss(latency, 1.0)),
                error=rng.random() < err,
            )
        )
    return scores


def test_math_helpers() -> None:
    assert js_divergence({"a": 1}, {"a": 5}) == 0
    assert js_divergence({"a": 1}, {"b": 1}) == pytest.approx(1.0)
    assert 0 < js_divergence({"a": 1, "b": 1}, {"a": 3, "b": 1}) < 1
    assert p99(list(range(1, 101))) == 99
    assert p99([5.0]) == 5.0


def test_budget_validation() -> None:
    with pytest.raises(ValueError):
        Budget(alert_at=10, limit_at=5)
    with pytest.raises(ValueError):
        Budget(baseline_n=1)
    with pytest.raises(ValueError):
        Budget(on_breach="MAYBE")
    with pytest.raises(ValueError, match="unknown budget keys"):
        Budget.from_mapping({"p99": 1})
    assert ChaosBudget is Budget
    b = ChaosBudget(p99_ms=300, error_rate=0.02)
    assert Budget.from_mapping(b.to_dict()) == b


def test_calibration_then_clean_traffic_stays_in_budget() -> None:
    rng = random.Random(1)
    m = Monitor(Budget(baseline_n=30))
    feed(m, 29, rng=rng)
    assert m.baseline("x") is None
    feed(m, 1, rng=rng)
    b = m.baseline("x")
    assert b is not None and b.n == 30 and 8 < b.latency_mean < 12
    feed(m, 300, rng=rng)
    assert m.finding("x") is None
    assert m.status()["agents"]["x"]["level"] == "GO"


def test_latency_shift_escalates_alert_limit_block() -> None:
    rng = random.Random(2)
    m = Monitor(Budget(baseline_n=30))
    feed(m, 30, rng=rng)
    seen = []
    for _ in range(40):
        feed(m, 1, rng=rng, latency=30.0)
        f = m.finding("x")
        seen.append(f.level if f else Level.GO)
    order = [lv for i, lv in enumerate(seen) if i == 0 or lv != seen[i - 1]]
    assert order[-3:] == [Level.ALERT, Level.LIMIT, Level.BLOCK]
    assert "accumulated deviation" in (m.finding("x").reason)  # type: ignore[union-attr]


def test_error_burst_and_repeats_raise_deviation() -> None:
    rng = random.Random(3)
    m = Monitor(Budget(baseline_n=30))
    feed(m, 30, rng=rng)
    a = Action("a", {"same": 1}, agent="x")
    scores = [m.record(a, latency_ms=10, error=True) for _ in range(5)]
    assert all(s > 3 for s in scores[1:])
    assert m.status()["agents"]["x"]["terms"]["repeat"] > 0


def test_tool_distribution_drift() -> None:
    rng = random.Random(4)
    m = Monitor(Budget(baseline_n=40, window=30, min_samples=20))
    feed(m, 40, rng=rng, tools=("a", "b"))
    feed(m, 30, rng=rng, tools=("c",))
    terms = m.status()["agents"]["x"]["terms"]
    assert terms["drift"] > 5


def test_envelope_without_calibration() -> None:
    m = Monitor(ChaosBudget(p99_ms=50, error_rate=0.1, min_samples=10, baseline_n=1000))
    rng = random.Random(5)
    feed(m, 10, rng=rng, latency=10)
    assert m.finding("x") is None
    feed(m, 10, rng=rng, latency=100)
    f = m.finding("x")
    assert f is not None and f.level is Level.LIMIT and "p99 latency" in f.reason


def test_cost_and_token_caps() -> None:
    m = Monitor(Budget(max_cost=1.0, max_tokens=100, on_breach="BLOCK"))
    m.record_usage("x", tokens=60, cost=0.6)
    assert m.finding("x") is None
    m.record_usage("x", tokens=60, cost=0.6)
    f = m.finding("x")
    assert f is not None and f.level is Level.BLOCK and "cost" in f.reason and "tokens" in f.reason


def test_gate_uses_budget_and_reset_clears_accumulated() -> None:
    rng = random.Random(6)
    m = Monitor(Budget(baseline_n=20))
    g = Gate(mode="enforce", monitor=m)
    feed(m, 20, rng=rng)
    for _ in range(60):
        feed(m, 1, rng=rng, latency=40)
    d = g.decide(Action("a", agent="x"))
    assert d.verdict is Level.BLOCK and not d.allowed and d.safe_state
    assert d.findings[0].axiom == "budget"
    g.reset("x")
    assert m.status()["agents"]["x"]["accumulated"] == 0
    assert g.decide(Action("a", agent="x")).allowed


def test_baseline_roundtrip_and_preload() -> None:
    rng = random.Random(7)
    m = Monitor(Budget(baseline_n=20))
    feed(m, 20, rng=rng)
    b = m.baseline("x")
    assert b is not None
    m2 = Monitor(Budget(baseline_n=20), baselines={"x": Baseline.from_dict(b.to_dict())})
    feed(m2, 5, rng=rng, latency=60)
    assert m2.status()["agents"]["x"]["accumulated"] > 0


def test_agents_are_independent() -> None:
    rng = random.Random(8)
    m = Monitor(Budget(baseline_n=20))
    feed(m, 20, rng=rng, agent="x")
    feed(m, 20, rng=rng, agent="y")
    feed(m, 40, rng=rng, agent="x", latency=50)
    assert m.finding("x") is not None and m.finding("y") is None
