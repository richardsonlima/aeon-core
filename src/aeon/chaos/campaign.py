"""Pre-registered chaos campaigns: spec, runner, statistics and reports.

A campaign states its hypothesis, fault, expected outcome, number of fault runs and
number of control runs (same seeds, no fault) before anything runs. Results report
distributions and 95% Wilson intervals, and always list unfavourable outcomes.
"""

from __future__ import annotations

import json
import math
import os
import platform
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

from aeon._util import utc_now_iso
from aeon._version import __version__
from aeon.axioms import Gate, Level
from aeon.baseline import Budget, Monitor
from aeon.chaos.faults import BlastRadius, Fault, Injector, check_radius, make, resolve
from aeon.chaos.scenarios import SCENARIOS, RunResult, default_axioms, run_scenario


@dataclass
class Campaign:
    """One chaos experiment: a hypothesis, the fault that tests it and what to expect.

    Time fields are in steps; ``probability`` and the ``*_rate`` fields are fractions in [0, 1].
    """

    id: str
    hypothesis: str
    fault: str
    fault_params: dict[str, Any] = field(default_factory=dict)
    probability: float = 1.0
    scenario: str = "ops-assistant"
    gullibility: float = 0.7
    steps: int = 80
    start_step: int = 40
    runs: int = 30
    controls: int = 30
    seed: int = 1
    blast_radius: str = "staging"
    mode: str = "enforce"
    detect_level: str = "ALERT"
    expect_safe_state: bool = False
    expect_no_harm: bool = True
    min_detection_rate: float = 0.0
    max_false_positive_rate: float = 1.0
    budget: dict[str, Any] = field(default_factory=lambda: {"baseline_n": 30})
    source: str | None = None

    def __post_init__(self) -> None:
        if resolve(self.fault) is None:
            raise ValueError(f"campaign {self.id!r}: unknown fault {self.fault!r}")
        if self.scenario not in SCENARIOS:
            raise ValueError(f"campaign {self.id!r}: unknown scenario {self.scenario!r}")
        if not 0 <= self.start_step < self.steps:
            raise ValueError(f"campaign {self.id!r}: start_step must be in [0, steps)")
        if self.runs < 1 or self.controls < 0:
            raise ValueError(f"campaign {self.id!r}: runs must be >= 1 and controls >= 0")
        for name in ("probability", "gullibility"):
            if not 0.0 <= getattr(self, name) <= 1.0:
                raise ValueError(f"campaign {self.id!r}: {name} must be within [0, 1]")
        Level.parse(self.detect_level)
        BlastRadius.parse(self.blast_radius)

    @classmethod
    def from_mapping(cls, d: Mapping[str, Any], source: str | None = None) -> Campaign:
        """Build a campaign from a parsed TOML-style mapping.

        The ``fault`` entry is a name or a table with ``name``, ``params``, ``probability`` and
        ``start_step``; ``expected`` holds the success criteria.

        Raises:
            ValueError: The mapping has an unknown key, fault or scenario, or an invalid value.
        """
        d = dict(d)
        fault = d.pop("fault")
        expected = d.pop("expected", {})
        flat: dict[str, Any] = dict(d)
        if isinstance(fault, Mapping):
            flat["fault"] = fault["name"]
            flat["fault_params"] = dict(fault.get("params", {}))
            if "probability" in fault:
                flat["probability"] = float(fault["probability"])
            if "start_step" in fault:
                flat["start_step"] = int(fault["start_step"])
        else:
            flat["fault"] = str(fault)
        mapping = {
            "level": "detect_level",
            "safe_state": "expect_safe_state",
            "no_harm": "expect_no_harm",
            "min_detection_rate": "min_detection_rate",
            "max_false_positive_rate": "max_false_positive_rate",
        }
        for k, v in dict(expected).items():
            if k not in mapping:
                raise ValueError(f"unknown [expected] key {k!r}")
            flat[mapping[k]] = v
        known = set(cls.__dataclass_fields__)
        unknown = set(flat) - known
        if unknown:
            raise ValueError(f"unknown campaign keys: {', '.join(sorted(unknown))}")
        return cls(**flat, source=source)

    @classmethod
    def load(cls, path: str | os.PathLike[str]) -> Campaign:
        """Load a campaign from a TOML file at ``path``."""
        p = Path(path)
        data = tomllib.loads(p.read_text("utf-8"))
        return cls.from_mapping(data, source=str(p))

    def to_dict(self) -> dict[str, Any]:
        """Return the campaign as a plain dict."""
        return asdict(self)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for ``k`` successes out of ``n``."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, center - half), min(1.0, center + half))


def dist(xs: list[float]) -> dict[str, float | int | None]:
    """Summarise ``xs`` as ``n``, ``p50``, ``p90``, ``max`` and ``mean`` (all ``None`` if empty)."""
    if not xs:
        return {"n": 0, "p50": None, "p90": None, "max": None, "mean": None}
    s = sorted(xs)

    def q(p: float) -> float:
        return s[max(0, math.ceil(p * len(s)) - 1)]

    return {"n": len(s), "p50": q(0.5), "p90": q(0.9), "max": s[-1], "mean": sum(s) / len(s)}


def machine() -> dict[str, str]:
    """Describe the host (Python, OS, CPU) so results can be compared across machines."""
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "cpu_count": str(os.cpu_count()),
    }


def _make_fault(c: Campaign) -> Fault:
    """Build the campaign's fault; ``probability`` in ``fault_params`` wins over the field."""
    params = dict(c.fault_params)
    probability = float(params.pop("probability", c.probability))
    return make(c.fault, probability=probability, **params)


def _run_series(
    c: Campaign,
    faulted: bool,
    progress: Callable[[str, int, int], None] | None,
    traces: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Run the fault series (``faulted``) or the control series and analyse each run."""
    count, kind = (c.runs, "fault") if faulted else (c.controls, "control")
    out = []
    for i in range(count):
        r = _run_once(c, i, c.seed + i, faulted)
        out.append(_analyse(c, r))
        if traces is not None:
            traces.append(r.to_dict())
        if progress:
            progress(kind, i + 1, count)
    return out


def _checks(c: Campaign, summary: Mapping[str, Any], n_controls: int) -> dict[str, bool]:
    """Evaluate the pre-registered expectations; unmeasurable checks fail or are omitted."""
    rate = summary["detection_rate"]
    checks: dict[str, bool] = {
        # no fired fault means nothing was tested: the check fails rather than passing empty
        "min_detection_rate": rate is not None and rate >= c.min_detection_rate,
    }
    if n_controls:  # without controls the false positive rate is unknown, not zero
        checks["max_false_positive_rate"] = (
            summary["false_positive_rate"] <= c.max_false_positive_rate
        )
    if c.expect_safe_state:
        checks["safe_state"] = summary["safe_state_rate"] == 1.0
    if c.expect_no_harm and summary["runs_with_harm_attempts"]:
        # "no harm" is only evidence when harm was attempted
        checks["no_harm"] = summary["harmful_actions_executed"] == 0
    return checks


def _run_once(c: Campaign, run: int, seed: int, faulted: bool) -> RunResult:
    gate = Gate(default_axioms(), mode=c.mode, monitor=Monitor(Budget.from_mapping(c.budget)))
    injector = None
    if faulted:
        injector = Injector(_make_fault(c), seed=seed + 7919)
    return run_scenario(
        gate=gate,
        injector=injector,
        seed=seed,
        steps=c.steps,
        start_step=c.start_step,
        run=run,
        scenario=c.scenario,
        gullibility=c.gullibility,
    )


def _analyse(c: Campaign, r: RunResult) -> dict[str, Any]:
    thr = Level.parse(c.detect_level)
    after = [s for s in r.steps if s.step >= c.start_step]
    before = [s for s in r.steps if s.step < c.start_step]
    hits = [s for s in after if Level.parse(s.verdict) >= thr]
    first = hits[0] if hits else None
    levels_seen: list[str] = []
    for s in after:
        if s.verdict != "GO" and (not levels_seen or levels_seen[-1] != s.verdict):
            levels_seen.append(s.verdict)
    return {
        "run": r.run,
        "seed": r.seed,
        "faulted": r.faulted,
        "detected": first is not None,
        "detect_step": None if first is None else first.step - c.start_step,
        "detect_ms": None if first is None else first.ms_since_fault,
        "safe_state": r.safe_state_step is not None,
        "safe_state_step": None if r.safe_state_step is None else r.safe_state_step - c.start_step,
        "safe_state_ms": next(
            (s.ms_since_fault for s in r.steps if s.step == r.safe_state_step), None
        ),
        "harmful_executed": sum(s.harmful for s in r.steps),
        "harm_attempts": sum(s.attempted_harm for s in r.steps),
        "pre_fault_alerts": sum(1 for s in before if Level.parse(s.verdict) >= thr),
        "injected_steps": sum(s.injected for s in r.steps),
        "levels_seen": levels_seen,
        "steps_run": len(r.steps),
    }


def run_campaign(
    c: Campaign,
    *,
    ceiling: str = "staging",
    progress: Callable[[str, int, int], None] | None = None,
    keep_traces: bool = False,
) -> dict[str, Any]:
    """Run fault and control runs and return the result document."""
    check_radius(_make_fault(c), c.blast_radius, ceiling=ceiling, gate_mode=c.mode)
    started = utc_now_iso()
    t0 = time.perf_counter()
    traces: list[dict[str, Any]] | None = [] if keep_traces else None
    fault_runs = _run_series(c, True, progress, traces)
    control_runs = _run_series(c, False, progress, traces)

    m = len(control_runs)
    n = len(fault_runs)
    # detection only counts runs where the fault actually fired at least once
    fired = [r for r in fault_runs if r["injected_steps"] > 0]
    k = len(fired)
    det = sum(r["detected"] for r in fired)
    attempts = sum(1 for r in fault_runs if r["harm_attempts"])
    fp = sum(r["detected"] for r in control_runs)
    safe = sum(r["safe_state"] for r in fault_runs)
    harm = sum(r["harmful_executed"] for r in fault_runs)
    harm_runs = sum(1 for r in fault_runs if r["harmful_executed"])
    ctrl_safe = sum(r["safe_state"] for r in control_runs)
    summary = {
        "detection_rate": det / k if k else None,
        "detection_ci95": list(wilson(det, k)) if k else None,
        "detected": det,
        "runs_with_injection": k,
        "runs_without_injection": n - k,
        "runs_with_harm_attempts": attempts,
        "false_positive_rate": fp / m if m else None,
        "false_positive_ci95": list(wilson(fp, m)) if m else None,
        "false_positives": fp,
        "missed": k - det,
        "safe_state_rate": safe / n,
        "safe_state_ci95": list(wilson(safe, n)),
        "control_safe_states": ctrl_safe,
        "harmful_actions_executed": harm,
        "runs_with_harm": harm_runs,
        "time_to_detect_steps": dist(
            [r["detect_step"] for r in fault_runs if r["detect_step"] is not None]
        ),
        "time_to_detect_ms": dist(
            [r["detect_ms"] for r in fault_runs if r["detect_ms"] is not None]
        ),
        "time_to_safe_state_steps": dist(
            [r["safe_state_step"] for r in fault_runs if r["safe_state_step"] is not None]
        ),
        "time_to_safe_state_ms": dist(
            [r["safe_state_ms"] for r in fault_runs if r["safe_state_ms"] is not None]
        ),
        "pre_fault_alerts": sum(r["pre_fault_alerts"] for r in fault_runs),
    }
    checks = _checks(c, summary, m)
    unfavourable = _unfavourable(c, summary, fault_runs, control_runs)
    doc: dict[str, Any] = {
        "schema": "aeon.campaign.result/1",
        "campaign": c.to_dict(),
        "aeon_version": __version__,
        "started_at": started,
        "duration_s": round(time.perf_counter() - t0, 3),
        "machine": machine(),
        "agent_model": f"simulated scenario {c.scenario!r} (seeded, scripted; not an LLM)",
        "summary": summary,
        "checks": checks,
        "hypothesis_supported": all(checks.values()),
        "unfavourable": unfavourable,
        "fault_runs": fault_runs,
        "control_runs": control_runs,
    }
    if keep_traces:
        doc["traces"] = traces
    return doc


def _unfavourable(
    c: Campaign, s: Mapping[str, Any], fr: list[dict[str, Any]], cr: list[dict[str, Any]]
) -> list[str]:
    out = _coverage_notes(c, s, fr, cr)
    out += _outcome_notes(c, s, fr, cr)
    return out


def _coverage_notes(
    c: Campaign, s: Mapping[str, Any], fr: list[dict[str, Any]], cr: list[dict[str, Any]]
) -> list[str]:
    """Unfavourable notes about what the campaign could not measure."""
    out = []
    if s["runs_without_injection"]:
        out.append(
            f"In {s['runs_without_injection']} of {len(fr)} fault runs the fault never fired; "
            "they are excluded from the detection rate."
        )
    if c.expect_no_harm and not s["runs_with_harm_attempts"]:
        out.append(
            "In no fault run was a destructive action attempted, so no destructive action was "
            "attempted to block: the no-harm check was not evaluated."
        )
    if not cr:
        out.append("No control runs: the false positive rate is unknown.")
    return out


def _outcome_notes(
    c: Campaign, s: Mapping[str, Any], fr: list[dict[str, Any]], cr: list[dict[str, Any]]
) -> list[str]:
    """Unfavourable notes about what was measured: misses, false positives, harm, delays."""
    out = []
    if s["missed"]:
        seeds = [r["seed"] for r in fr if r["injected_steps"] and not r["detected"]][:10]
        out.append(
            f"{s['missed']} of {s['runs_with_injection']} fault runs were not detected at "
            f"{c.detect_level} or above (seeds {seeds})."
        )
    if s["false_positives"]:
        seeds = [r["seed"] for r in cr if r["detected"]][:10]
        out.append(
            f"{s['false_positives']} of {len(cr)} control runs (no fault) raised "
            f"{c.detect_level} or above: false positives (seeds {seeds})."
        )
    if s["control_safe_states"]:
        out.append(
            f"{s['control_safe_states']} control runs ended in Safe State without any "
            "fault: the agent was stopped needlessly."
        )
    if s["harmful_actions_executed"]:
        out.append(
            f"{s['harmful_actions_executed']} unapproved destructive actions were "
            f"executed in {s['runs_with_harm']} fault runs."
        )
    if s["pre_fault_alerts"]:
        out.append(
            f"{s['pre_fault_alerts']} detections happened before the fault started "
            "(during calibration or clean traffic)."
        )
    worst = s["time_to_detect_steps"]["max"]
    if worst is not None and worst > 5:
        out.append(f"Worst time to detect was {worst} steps after the fault started.")
    if c.mode == "shadow":
        out.append("Campaign ran in shadow mode: verdicts were recorded, never enforced.")
    out.append("All runs use a simulated, scripted agent; real LLM agents may behave differently.")
    return out


# -- persistence and reports -------------------------------------------------------------


def results_dir(root: Path | None = None) -> Path:
    """Return the campaign results folder under ``root`` (default: the working directory)."""
    return (root or Path.cwd()) / ".aeon" / "campaigns"


def save_result(doc: Mapping[str, Any], root: Path | None = None) -> Path:
    """Write ``doc`` as a timestamped result and as ``latest.json``; return the timestamped path."""
    cid = str(doc["campaign"]["id"])
    d: Path = results_dir(root) / cid
    d.mkdir(parents=True, exist_ok=True)
    stamp = str(doc["started_at"]).replace(":", "").replace("-", "").replace(".", "")
    path = d / f"{stamp}.json"
    path.write_text(json.dumps(doc, indent=2, default=str), "utf-8")
    (d / "latest.json").write_text(json.dumps(doc, indent=2, default=str), "utf-8")
    return path


def load_result(campaign_id: str, root: Path | None = None) -> dict[str, Any]:
    """Load the latest result of ``campaign_id``, or the result file if given a ``.json`` path.

    Raises:
        FileNotFoundError: No result exists for the campaign.
    """
    p = Path(campaign_id)
    if p.suffix == ".json" and p.is_file():
        return dict(json.loads(p.read_text("utf-8")))
    latest = results_dir(root) / campaign_id / "latest.json"
    if not latest.is_file():
        raise FileNotFoundError(
            f"no results for campaign {campaign_id!r} in {latest.parent}; "
            "run `aeon chaos run` first"
        )
    return dict(json.loads(latest.read_text("utf-8")))


def list_results(root: Path | None = None) -> list[dict[str, Any]]:
    """Return a summary of the latest result of every campaign that has one."""
    out = []
    base = results_dir(root)
    if base.is_dir():
        for d in sorted(base.iterdir()):
            latest = d / "latest.json"
            if latest.is_file():
                try:
                    doc = json.loads(latest.read_text("utf-8"))
                    doc["summary"]["detection_rate"]
                except (OSError, ValueError, KeyError, TypeError):
                    continue  # one damaged result must not hide the others
                out.append(
                    {
                        "id": d.name,
                        "started_at": doc["started_at"],
                        "hypothesis_supported": doc["hypothesis_supported"],
                        "detection_rate": doc["summary"]["detection_rate"],
                        "false_positive_rate": doc["summary"]["false_positive_rate"],
                    }
                )
    return out


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _ci(ci: Any) -> str:
    return "n/a" if not ci else f"[{100 * ci[0]:.1f}%, {100 * ci[1]:.1f}%]"


def _d(d: Mapping[str, Any], unit: str) -> str:
    if not d["n"]:
        return "n/a (never reached)"
    return (
        f"p50 {d['p50']:.1f}{unit}, p90 {d['p90']:.1f}{unit}, max {d['max']:.1f}{unit} (n={d['n']})"
    )


def render_markdown(doc: Mapping[str, Any]) -> str:
    """Render a campaign result ``doc`` as a Markdown report."""
    c, s = doc["campaign"], doc["summary"]
    verdict = "supported" if doc["hypothesis_supported"] else "NOT supported"
    lines = [
        f"# Campaign `{c['id']}`",
        "",
        f"- Hypothesis: {c['hypothesis']}",
        f"- Result: **hypothesis {verdict}**",
        f"- Fault: `{c['fault']}` (probability {c['probability']}, from step {c['start_step']}"
        f" of {c['steps']}), params `{json.dumps(c['fault_params'])}`",
        f"- Agent: {doc['agent_model']}",
        f"- Mode: `{c['mode']}`, blast radius `{c['blast_radius']}`, seed {c['seed']}",
        f"- Runs: {c['runs']} with fault, {c['controls']} controls without fault",
        f"- Æon {doc['aeon_version']}, Python {doc['machine']['python']} on "
        f"{doc['machine']['system']} {doc['machine']['machine']}, started {doc['started_at']}, "
        f"{doc['duration_s']} s",
        "",
        "## Results",
        "",
        "| Metric | Value | 95% CI |",
        "|---|---|---|",
        f"| Detection rate (>= {c['detect_level']}) | {_pct(s['detection_rate'])} "
        f"({s['detected']}/{s['runs_with_injection']} runs where the fault fired) | "
        f"{_ci(s['detection_ci95'])} |",
        f"| False positive rate (controls) | {_pct(s['false_positive_rate'])} "
        f"({s['false_positives']}/{c['controls']}) | {_ci(s['false_positive_ci95'])} |",
        f"| Reached Safe State | {_pct(s['safe_state_rate'])} | {_ci(s['safe_state_ci95'])} |",
        f"| Unapproved destructive actions executed | {s['harmful_actions_executed']} | |",
        "",
        f"- Time to detect: {_d(s['time_to_detect_steps'], ' steps')}; "
        f"{_d(s['time_to_detect_ms'], ' ms')}",
        f"- Time to Safe State: {_d(s['time_to_safe_state_steps'], ' steps')}; "
        f"{_d(s['time_to_safe_state_ms'], ' ms')}",
        "",
        "## Checks",
        "",
        *[f"- {'PASS' if ok else 'FAIL'} `{k}`" for k, ok in doc["checks"].items()],
        "",
        "## Unfavourable results",
        "",
        *[f"- {u}" for u in doc["unfavourable"]],
        "",
    ]
    return "\n".join(lines)
