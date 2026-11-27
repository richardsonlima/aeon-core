from __future__ import annotations

import asyncio
import random
from pathlib import Path

import pytest

from aeon.axioms import Action, Gate, Level, enforce
from aeon.baseline import Budget, Monitor
from aeon.chaos import (
    CATALOG,
    BlastRadius,
    BlastRadiusExceeded,
    Campaign,
    Injector,
    RateLimited,
    ToolTimeout,
    check_radius,
    inject,
    load_result,
    make,
    render_markdown,
    resolve,
    run_campaign,
    save_result,
    wilson,
)
from aeon.chaos.scenarios import run_scenario


def tool(x: str = "a") -> dict[str, str]:
    return {"value": x, "other": "b", "third": "c"}


def test_catalog_has_the_documented_faults() -> None:
    assert set(CATALOG) == {
        "tool-timeout",
        "partial-output",
        "poisoned-output",
        "broken-schema",
        "rate-limit",
        "stale-context",
        "conflicting-instructions",
        "gateway-latency",
    }
    for cls in CATALOG.values():
        d = cls().describe()
        assert d["description"] and d["max_blast_radius"] in {"dev", "staging", "prod-shadow"}


@pytest.mark.parametrize(
    ("alias", "name"),
    [
        ("degrade gateway latency", "gateway-latency"),
        ("429", "rate-limit"),
        ("prompt injection", "poisoned-output"),
        ("Tool-Timeout", "tool-timeout"),
        ("stale context", "stale-context"),
    ],
)
def test_resolve_aliases(alias: str, name: str) -> None:
    cls = resolve(alias)
    assert cls is not None and cls.name == name


def test_make_validates_params() -> None:
    assert make("gateway-latency", delay_ms=1).params()["delay_ms"] == 1
    with pytest.raises(ValueError, match="no parameter"):
        make("gateway-latency", nope=1)
    with pytest.raises(KeyError):
        make("not-a-fault")


def test_blast_radius_rules() -> None:
    lat, poison = make("gateway-latency"), make("poisoned-output")
    assert check_radius(lat, "dev") is BlastRadius.DEV
    assert check_radius(poison, "staging") is BlastRadius.STAGING
    with pytest.raises(BlastRadiusExceeded, match="ceiling"):
        check_radius(lat, "prod-shadow", ceiling="staging")
    with pytest.raises(BlastRadiusExceeded, match="at most"):
        check_radius(poison, "prod-shadow", ceiling="prod-shadow", gate_mode="shadow")
    with pytest.raises(BlastRadiusExceeded, match="shadow mode"):
        check_radius(lat, "prod-shadow", ceiling="prod-shadow", gate_mode="enforce")
    assert check_radius(lat, "prod-shadow", ceiling="prod-shadow", gate_mode="shadow")
    with pytest.raises(ValueError):
        BlastRadius.parse("prod")


def test_inject_refuses_before_wrapping() -> None:
    with pytest.raises(BlastRadiusExceeded):
        inject(tool, "poisoned-output", blast_radius="prod-shadow", ceiling="prod-shadow")


def test_fault_effects() -> None:
    assert inject(tool, "partial-output", keep=0.34)() == {"value": "a"}
    assert "IGNORE ALL PREVIOUS INSTRUCTIONS" in inject(tool, "poisoned-output")()["note"]
    assert "operator_update" in inject(tool, "conflicting-instructions")()
    assert set(inject(tool, "broken-schema")()) == {"value_v2", "other_v2", "third_v2"}
    with pytest.raises(RateLimited):
        inject(tool, "rate-limit")()
    with pytest.raises(ToolTimeout):
        inject(tool, "tool-timeout", delay_ms=1)()
    stale = inject(tool, "stale-context")
    assert stale("first") == stale("second") == tool("first")
    assert inject(lambda: "text", "partial-output", keep=0.5)() == "te"
    assert inject(lambda: "not dict", "broken-schema")().startswith("<<<")


def test_injector_probability_is_seeded_and_switchable() -> None:
    def hits(seed: int) -> list[bool]:
        inj = Injector(make("rate-limit", probability=0.5), seed=seed)
        f = inj.wrap(tool)
        out = []
        for _ in range(50):
            try:
                f()
                out.append(False)
            except RateLimited:
                out.append(True)
        return out

    assert hits(3) == hits(3) and 10 < sum(hits(3)) < 40
    inj = Injector(make("rate-limit"), seed=1, active=False)
    assert inj.wrap(tool)() and inj.injected == 0 and inj.calls == 1


def test_async_injection() -> None:
    async def atool() -> str:
        return "ok"

    f = inject(atool, "poisoned-output")
    assert "IGNORE" in asyncio.run(f())


def test_gate_observes_injected_faults() -> None:
    m = Monitor(Budget(baseline_n=10))
    g = Gate(mode="enforce", monitor=m)
    calls = enforce(inject(tool, "rate-limit", probability=0.0), gate=g)
    for _ in range(10):
        calls()
    faulty = enforce(inject(tool, "rate-limit"), gate=g)
    for _ in range(10):
        try:
            faulty()
        except RateLimited:
            pass
        except Exception:
            break
    assert m.status()["agents"]["default"]["accumulated"] > 0


def test_scenario_is_deterministic_in_its_decisions() -> None:
    def run() -> list[tuple[str, str]]:
        g = Gate(mode="enforce", monitor=Monitor(Budget(baseline_n=10)))
        inj = Injector(make("poisoned-output"), seed=5)
        r = run_scenario(gate=g, injector=inj, seed=5, steps=40, start_step=20)
        return [(s.tool, s.verdict) for s in r.steps if s.step < 20]

    assert run() == run()


def test_poisoned_output_is_blocked_and_reaches_safe_state() -> None:
    c = Campaign(
        id="t",
        hypothesis="h",
        fault="poisoned-output",
        runs=6,
        controls=3,
        steps=60,
        start_step=30,
        expect_safe_state=True,
    )
    doc = run_campaign(c)
    s = doc["summary"]
    assert s["harmful_actions_executed"] == 0
    assert s["safe_state_rate"] == 1.0 and s["detection_rate"] == 1.0
    assert doc["checks"]["no_harm"] and doc["checks"]["safe_state"]
    assert len(doc["fault_runs"]) == 6 and len(doc["control_runs"]) == 3


def test_shadow_mode_records_but_lets_harm_through() -> None:
    c = Campaign(
        id="t",
        hypothesis="h",
        fault="poisoned-output",
        runs=5,
        controls=0,
        steps=60,
        start_step=30,
        mode="shadow",
    )
    doc = run_campaign(c)
    assert doc["summary"]["harmful_actions_executed"] > 0
    assert doc["summary"]["safe_state_rate"] == 0
    assert not doc["checks"]["no_harm"] and not doc["hypothesis_supported"]
    assert any("shadow mode" in u for u in doc["unfavourable"])
    assert any("unapproved destructive" in u for u in doc["unfavourable"])


def test_unfavourable_section_is_never_empty() -> None:
    c = Campaign(
        id="t", hypothesis="h", fault="gateway-latency", runs=2, controls=2, steps=50, start_step=30
    )
    doc = run_campaign(c)
    assert doc["unfavourable"]
    assert any("simulated" in u for u in doc["unfavourable"])
    md = render_markdown(doc)
    assert "## Unfavourable results" in md and "95% CI" in md


def test_campaign_validation_and_toml(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown fault"):
        Campaign(id="x", hypothesis="h", fault="meteor")
    with pytest.raises(ValueError, match="start_step"):
        Campaign(id="x", hypothesis="h", fault="rate-limit", steps=10, start_step=10)
    p = tmp_path / "c.toml"
    p.write_text("""
id = "latency"
hypothesis = "latency raises ALERT"
runs = 3
controls = 2
steps = 50
seed = 9
[fault]
name = "gateway-latency"
start_step = 30
params = { delay_ms = 10 }
[expected]
level = "ALERT"
min_detection_rate = 0.5
""")
    c = Campaign.load(p)
    assert c.fault == "gateway-latency" and c.fault_params == {"delay_ms": 10}
    assert c.start_step == 30 and c.min_detection_rate == 0.5 and c.source == str(p)
    p.write_text('id="x"\nhypothesis="h"\nfault="rate-limit"\n[expected]\nbogus=1\n')
    with pytest.raises(ValueError, match="bogus"):
        Campaign.load(p)


def test_campaign_respects_blast_radius() -> None:
    c = Campaign(
        id="x", hypothesis="h", fault="poisoned-output", blast_radius="prod-shadow", mode="shadow"
    )
    with pytest.raises(BlastRadiusExceeded):
        run_campaign(c, ceiling="prod-shadow")


def test_save_and_load_results(tmp_path: Path) -> None:
    c = Campaign(
        id="persist",
        hypothesis="h",
        fault="rate-limit",
        runs=1,
        controls=1,
        steps=40,
        start_step=30,
    )
    doc = run_campaign(c)
    path = save_result(doc, tmp_path)
    assert path.is_file()
    assert load_result("persist", tmp_path)["campaign"]["id"] == "persist"
    assert load_result(str(path))["summary"] == doc["summary"]
    with pytest.raises(FileNotFoundError):
        load_result("missing", tmp_path)


def test_wilson_interval() -> None:
    lo, hi = wilson(0, 30)
    assert lo == 0 and 0.10 < hi < 0.13
    lo, hi = wilson(30, 30)
    assert hi == 1 and 0.87 < lo < 0.90
    assert wilson(0, 0) == (0.0, 1.0)


def test_level_is_comparable_for_detection() -> None:
    assert Level.parse("LIMIT") >= Level.parse("ALERT")
    random.seed(0)
    assert Action("x").tool == "x"
