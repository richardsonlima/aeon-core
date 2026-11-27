"""Run every benchmark, write results/summary.md, then regenerate docs/claims.yaml.

python benchmarks/run_all.py            # full run (a few minutes)
python benchmarks/run_all.py --quick    # fewer samples, for a smoke check
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent


def run(script: str, *args: str) -> None:
    print(f"\n$ python benchmarks/{script} {' '.join(args)}", flush=True)
    subprocess.run([sys.executable, str(HERE / script), *args], check=True, cwd=ROOT)


def summary() -> str:
    r = HERE / "results"
    gate = json.loads((r / "gate_latency.json").read_text())
    audit = json.loads((r / "audit_overhead.json").read_text())
    det = json.loads((r / "detection.json").read_text())
    m = gate["machine"]
    lines = [
        "# Benchmark summary",
        "",
        f"Generated {gate['date']} by `python benchmarks/run_all.py` with Æon "
        f"{gate['aeon_version']} on {m.get('cpu', m['machine'])}, {m['system']} "
        f"{m['release']}, Python {m['python']}, {m['cpu_count']} CPUs.",
        "These numbers describe this machine only.",
        "",
        "## Gate decision latency (µs per decide, audit off)",
        "",
        f"{gate['parameters']['samples']} samples per row, "
        f"{gate['parameters']['warmup_excluded']} warmup calls excluded.",
        "",
        "| Axioms | Mode | Monitor | p50 | p90 | p99 | max |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in gate["rows"]:
        s = row["latency_us"]
        lines.append(
            f"| {row['axioms']} | {row['mode']} | {row['monitor']} | {s['p50']:.2f} | "
            f"{s['p90']:.2f} | {s['p99']:.2f} | {s['max']:.1f} |"
        )
    lines += [
        "",
        "## Audit",
        "",
        "| Scenario | emit p50 µs | emit p99 µs | emit max µs | "
        "dropped | durable lag p50 ms | lag p99 ms | lag max ms |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for key, label in (
        ("burst", f"burst of {audit['burst']['events']} events, no pause"),
        ("paced_1000_per_s", "paced 1000/s"),
        ("paced_500_per_s_fsync", "paced 500/s, fsync"),
    ):
        a = audit[key]
        e, lag = a["emit_us"], a["durable_lag_ms"]
        lines.append(
            f"| {label} | {e['p50']:.2f} | {e['p99']:.2f} | {e['max']:.1f} | "
            f"{a['dropped']} | {lag['p50']:.2f} | {lag['p99']:.2f} | {lag['max']:.1f} |"
        )
    g = audit["gate_decide_us"]
    lines += [
        "",
        f"Gate.decide without audit: p50 {g['no_audit']['p50']:.2f} µs, p99 "
        f"{g['no_audit']['p99']:.2f} µs, max {g['no_audit']['max']:.1f} µs. With a JSONL "
        f"audit log: p50 {g['jsonl_audit']['p50']:.2f} µs, p99 {g['jsonl_audit']['p99']:.2f}"
        f" µs, max {g['jsonl_audit']['max']:.1f} µs (dropped {g['dropped']}).",
        f"Chain verify: {audit['verify']['records_per_s']:.0f} records/s.",
        "",
        "## Detection (simulated agent, 30 fault runs + 30 controls each)",
        "",
        "| Campaign | Level | Detection [95% CI] | False positives [95% CI] | Safe State | "
        "Harmful actions run | Hypothesis |",
        "|---|---|---|---|---|---|---|",
    ]

    def pct(x: float | None) -> str:
        return "n/a" if x is None else f"{100 * x:.0f}%"

    def ci(x: list[float] | None) -> str:
        return "n/a" if not x else f"[{100 * x[0]:.0f}, {100 * x[1]:.0f}]"

    for row in det["rows"]:
        lines.append(
            f"| {row['id']} | {row['detect_level']} | {pct(row['detection_rate'])} "
            f"{ci(row['detection_ci95'])} | {100 * (row['false_positive_rate'] or 0):.0f}% "
            f"{ci(row['false_positive_ci95'])} | {100 * row['safe_state_rate']:.0f}% | "
            f"{row['harmful_actions_executed']} | "
            f"{'supported' if row['hypothesis_supported'] else 'NOT supported'} |"
        )
    lines += [
        "",
        "Per-campaign reports, including every unfavourable result: "
        "[`results/campaigns/`](results/campaigns/).",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    if a.quick:
        run("bench_gate.py", "--samples", "5000", "--warmup", "500")
        run("bench_audit.py", "--events", "5000")
    else:
        run("bench_gate.py")
        run("bench_audit.py")
    run("bench_detection.py")
    (HERE / "results" / "summary.md").write_text(summary(), "utf-8")
    print("\nwrote benchmarks/results/summary.md")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "claims.py")], check=True, cwd=ROOT)


if __name__ == "__main__":
    main()
