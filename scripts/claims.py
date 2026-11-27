"""Generate docs/claims.yaml and docs/claims.json from evidence. Do not edit those by hand.

Status ladder:
- specified: described in docs, no evidence in the repo yet.
- implemented: every referenced test exists (CI runs them).
- measured: implemented, and a committed benchmark result satisfies the claim.
A claim whose measurement misses its target stays "implemented" with a note saying so.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "benchmarks" / "results"


def result(name: str) -> dict[str, Any] | None:
    p = RESULTS / f"{name}.json"
    return json.loads(p.read_text()) if p.is_file() else None


def gate_rows() -> list[dict[str, Any]]:
    g = result("gate_latency")
    return g["rows"] if g else []


def detection(cid: str) -> dict[str, Any] | None:
    d = result("detection")
    return next((r for r in d["rows"] if r["id"] == cid), None) if d else None


Measure = Callable[[], tuple[bool, str] | None]


@dataclass
class Claim:
    id: str
    text: str
    tests: list[str] = field(default_factory=list)
    docs: list[str] = field(default_factory=list)
    measure: Measure | None = None
    benchmark: str | None = None


def m_gate_p99(limit_us: float, axioms: int) -> Measure:
    def f() -> tuple[bool, str] | None:
        rows = [r for r in gate_rows() if r["axioms"] == axioms and r["monitor"]]
        if not rows:
            return None
        worst = max(r["latency_us"]["p99"] for r in rows)
        return worst < limit_us, f"p99 {worst:.2f} µs with {axioms} axioms (limit {limit_us:g} µs)"

    return f


def m_gate_max(limit_us: float) -> Measure:
    def f() -> tuple[bool, str] | None:
        rows = gate_rows()
        if not rows:
            return None
        worst = max(r["latency_us"]["max"] for r in rows)
        return worst < limit_us, f"worst max {worst:.1f} µs over all rows (limit {limit_us:g} µs)"

    return f


def m_emit_p50(limit_us: float) -> Measure:
    def f() -> tuple[bool, str] | None:
        a = result("audit_overhead")
        if not a:
            return None
        v = a["paced_1000_per_s"]["emit_us"]["p50"]
        mx = a["burst"]["emit_us"]["max"]
        return v < limit_us, f"emit p50 {v:.2f} µs at 1000/s; burst max {mx:.1f} µs"

    return f


def m_no_drop_paced() -> Measure:
    def f() -> tuple[bool, str] | None:
        a = result("audit_overhead")
        if not a:
            return None
        d = a["paced_1000_per_s"]["dropped"]
        return d == 0, f"{d} dropped at 1000/s paced; burst dropped {a['burst']['dropped']}"

    return f


def m_no_harm(*cids: str) -> Measure:
    def f() -> tuple[bool, str] | None:
        rows = [detection(c) for c in cids]
        if any(r is None for r in rows):
            return None
        harm = sum(r["harmful_actions_executed"] for r in rows if r)
        runs = sum(r["runs"] for r in rows if r)
        return harm == 0, f"{harm} unapproved destructive actions executed in {runs} fault runs"

    return f


def m_fp_rate(limit: float) -> Measure:
    def f() -> tuple[bool, str] | None:
        d = result("detection")
        if not d:
            return None
        rows = [r for r in d["rows"] if r["mode"] == "enforce"]
        worst = max(rows, key=lambda r: r["false_positive_rate"] or 0)
        v = worst["false_positive_rate"] or 0
        return v <= limit, (
            f"worst false positive rate {100 * v:.0f}% ({worst['id']}, "
            f"level {worst['detect_level']}); target {100 * limit:.0f}%"
        )

    return f


CLAIMS = [
    Claim(
        "gate-before-execution",
        "Every call through an enforced executor is decided by the gate before the executor "
        "runs; a BLOCK verdict in enforce mode prevents the call.",
        tests=[
            "tests/test_gate.py::test_block_stops_action_and_enters_safe_state",
            "tests/test_gate.py::test_enforce_function_tool",
        ],
        docs=["docs/concepts/gate.md"],
    ),
    Claim(
        "safe-state",
        "After BLOCK the agent is held in Safe State and every later action of "
        "that agent is blocked until it is reset.",
        tests=["tests/test_gate.py::test_block_stops_action_and_enters_safe_state"],
    ),
    Claim(
        "shadow-default",
        "New installs run in shadow mode: verdicts are recorded and never enforced.",
        tests=[
            "tests/test_gate.py::test_new_gate_defaults_to_shadow",
            "tests/test_gate.py::test_shadow_never_enforces",
            "tests/test_cli.py::test_init_is_shadow_and_does_not_overwrite",
        ],
    ),
    Claim(
        "fail-closed",
        "If an axiom or the gate itself raises, the action is blocked in "
        "enforce mode and allowed but logged in shadow mode.",
        tests=[
            "tests/test_gate.py::test_axiom_raising_blocks_in_enforce",
            "tests/test_gate.py::test_axiom_raising_allows_and_logs_in_shadow",
            "tests/test_gate.py::test_gate_internal_error_fails_closed",
        ],
    ),
    Claim(
        "kill-switch",
        "The kill-switch blocks every action of every agent, in shadow and enforce mode.",
        tests=["tests/test_gate.py::test_kill_switch_blocks_everything_even_in_shadow"],
    ),
    Claim(
        "audit-tamper-evident",
        "`aeon audit verify` detects a changed, removed, reordered or "
        "corrupted record and reports the first broken link.",
        tests=[
            "tests/test_audit.py::test_detects_modified_record",
            "tests/test_audit.py::test_detects_deleted_record",
            "tests/test_audit.py::test_detects_reordered_records",
            "tests/test_audit.py::test_detects_corrupted_line",
            "tests/test_audit.py::test_property_any_single_change_is_detected",
            "tests/test_cli.py::test_audit_verify_pinpoints_tampering",
        ],
    ),
    Claim(
        "audit-truncation",
        "Removing records from the end of the log is detected only when "
        "the expected head hash is supplied (`--expect-head`).",
        tests=["tests/test_audit.py::test_truncation_needs_expected_head"],
        docs=["docs/known-limits.md"],
    ),
    Claim(
        "audit-off-path",
        "Audit writing happens on a background thread; a storage outage "
        "does not change decisions and is itself recorded once storage recovers.",
        tests=[
            "tests/test_audit.py::test_backend_outage_is_recorded_and_recovered",
            "tests/test_gate.py::test_audit_sink_failure_does_not_break_decisions",
        ],
    ),
    Claim(
        "gate-p99-100us",
        "Gate decision latency p99 is under 100 µs with 10 axioms (reference machine, audit off).",
        measure=m_gate_p99(100, 10),
        benchmark="benchmarks/results/gate_latency.json",
    ),
    Claim(
        "gate-p99-100us-100-axioms",
        "Gate decision latency p99 is under 100 µs with 100 axioms (reference machine, audit off).",
        measure=m_gate_p99(100, 100),
        benchmark="benchmarks/results/gate_latency.json",
    ),
    Claim(
        "gate-max-1ms",
        "No single gate decision took 1 ms or more in the benchmark "
        "(reference machine, audit off).",
        measure=m_gate_max(1000),
        benchmark="benchmarks/results/gate_latency.json",
    ),
    Claim(
        "audit-emit-cheap",
        "Emitting an audit event costs under 10 µs at the median on the decision path.",
        measure=m_emit_p50(10),
        benchmark="benchmarks/results/audit_overhead.json",
    ),
    Claim(
        "audit-no-drop-paced",
        "At 1000 events/s the audit queue drops no events.",
        measure=m_no_drop_paced(),
        benchmark="benchmarks/results/audit_overhead.json",
    ),
    Claim(
        "no-harm-injection",
        "In enforce mode, prompt-injected and conflicting instructions "
        "in tool output led to no executed unapproved destructive action (simulated agent).",
        tests=["tests/test_chaos.py::test_poisoned_output_is_blocked_and_reaches_safe_state"],
        measure=m_no_harm("poisoned-output", "conflicting-instructions"),
        benchmark="benchmarks/results/detection.json",
    ),
    Claim(
        "false-positives-10pct",
        "Target: clean control runs raise the campaign's detection "
        "level in at most 10% of runs (simulated agent).",
        measure=m_fp_rate(0.10),
        benchmark="benchmarks/results/detection.json",
    ),
    Claim(
        "blast-radius",
        "Faults refuse to run above their declared blast radius or the "
        "configured ceiling; prod-shadow requires shadow mode.",
        tests=[
            "tests/test_chaos.py::test_blast_radius_rules",
            "tests/test_cli.py::test_chaos_run_guards",
        ],
    ),
    Claim(
        "no-telemetry",
        "Æon sends no telemetry. Nothing leaves the machine unless your own code sends it.",
        docs=["docs/security.md"],
    ),
    Claim(
        "runtime-local-token",
        "The runtime requires a bearer token on /v1 routes and refuses "
        "to bind a non-loopback address unless explicitly allowed.",
        tests=[
            "tests/test_runtime.py::test_v1_requires_token",
            "tests/test_runtime.py::test_remote_bind_refused",
        ],
    ),
    Claim(
        "mcp-tools",
        "The runtime exposes aeon_check_action, aeon_status, aeon_audit_verify "
        "and aeon_run_campaign over MCP (stdio).",
        tests=["tests/test_mcp.py::test_tools_list_names_and_schemas"],
    ),
    Claim(
        "audit-signing",
        "Roadmap: signed audit records and an external anchor for the chain head. Not implemented.",
        docs=["docs/known-limits.md"],
    ),
]


def test_exists(node: str) -> bool:
    path, _, name = node.partition("::")
    p = ROOT / path
    return (
        p.is_file()
        and re.search(rf"^\s*(async )?def {re.escape(name)}\(", p.read_text(), re.M) is not None
    )


def evaluate(c: Claim) -> dict[str, Any]:
    missing = [t for t in c.tests if not test_exists(t)]
    status = "implemented" if c.tests and not missing else "specified"
    note = None
    if missing:
        note = f"missing tests: {', '.join(missing)}"
    value = None
    if c.measure is not None:
        m = c.measure()
        if m is None:
            note = (note + "; " if note else "") + "no benchmark result committed"
        else:
            ok, value = m
            if c.tests and missing:
                pass
            elif ok:
                status = "measured"
            else:
                status = "implemented"
                note = f"target not met: {value}"
    evidence = [*c.tests, *c.docs] + ([c.benchmark] if c.benchmark else [])
    out: dict[str, Any] = {
        "id": c.id,
        "text": c.text,
        "status": status,
        "evidence": evidence,
        "last_checked": time.strftime("%Y-%m-%d"),
    }
    if value:
        out["value"] = value
    if note:
        out["note"] = note
    return out


def yaml_dump(rows: list[dict[str, Any]]) -> str:
    q = json.dumps  # a JSON string is a valid YAML double-quoted scalar
    lines = [
        "# Generated by scripts/claims.py from tests and benchmarks/results. Do not edit.",
        "claims:",
    ]
    for r in rows:
        lines.append(f"  - id: {r['id']}")
        for k in ("text", "status", "value", "note", "last_checked"):
            if k in r:
                lines.append(f"    {k}: {q(r[k], ensure_ascii=False)}")
        lines.append("    evidence:" if r["evidence"] else "    evidence: []")
        lines.extend(f"      - {q(e)}" for e in r["evidence"])
    return "\n".join(lines) + "\n"


def main() -> None:
    rows = [evaluate(c) for c in CLAIMS]
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "claims.yaml").write_text(yaml_dump(rows), "utf-8")
    (ROOT / "docs" / "claims.json").write_text(
        json.dumps({"claims": rows}, indent=2, ensure_ascii=False), "utf-8"
    )
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("claims:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    for r in rows:
        if "note" in r:
            print(f"  {r['id']}: {r['status']} ({r['note']})")


if __name__ == "__main__":
    main()
