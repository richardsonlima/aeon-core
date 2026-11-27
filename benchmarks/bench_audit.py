"""Audit overhead: cost of emit() on the decision path, lag until durable, verify rate.

- emit cost: time of AuditLog.emit (what the decision path pays), per event.
- durable lag: from emit to the backend append returning (flush to the OS; with
  fsync=True, to the disk). Measured by the writer thread.
- end-to-end gate cost: Gate.decide with a JSONL audit attached vs. no audit.
- verify throughput: records per second for aeon.audit.verify on the written file.
"""

from __future__ import annotations

import argparse
import tempfile
import time
from pathlib import Path

from _common import summarize, write

from aeon.audit import AuditLog, verify
from aeon.axioms import Action, AxiomSpec, Gate, Level


def emit_cost(path: Path, n: int, fsync: bool, rate_per_s: float | None) -> dict:
    log = AuditLog(path, fsync=fsync)
    data = {"agent": "a", "tool": "read_file", "verdict": "GO", "findings": []}
    ns = []
    gap = 1.0 / rate_per_s if rate_per_s else 0.0
    clock = time.perf_counter_ns
    for _ in range(n):
        t0 = clock()
        log.emit("decision", data)
        ns.append(clock() - t0)
        if gap:
            target = time.perf_counter() + gap
            while time.perf_counter() < target:
                pass
    ok = log.flush(120)
    log.close()
    lag = list(log.stats.lag_samples)
    return {
        "fsync": fsync,
        "events": n,
        "paced_rate_per_s": rate_per_s,
        "flushed": ok,
        "dropped": log.stats.dropped,
        "emit_us": summarize([x / 1e3 for x in ns]),
        "durable_lag_ms": summarize(lag) if lag else None,
        "lag_samples_kept": len(lag),
    }


def gate_with_audit(path: Path, n: int) -> dict:
    spec = AxiomSpec("r", lambda a: True, Level.BLOCK)
    act = Action("read_file", {"path": "/x"})
    out = {}
    for label, audit in (("no_audit", None), ("jsonl_audit", AuditLog(path))):
        g = Gate([spec], mode="enforce", audit=audit)
        for _ in range(5000):
            g.decide(act)
        ns = []
        for _ in range(n):
            t0 = time.perf_counter_ns()
            g.decide(act)
            ns.append(time.perf_counter_ns() - t0)
        if audit is not None:
            audit.flush(120)
            out["dropped"] = audit.stats.dropped
            audit.close()
        out[label] = summarize([x / 1e3 for x in ns])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=int, default=50_000)
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        burst = emit_cost(base / "burst.jsonl", a.events, False, None)
        paced = emit_cost(base / "paced.jsonl", 5_000, False, 1000.0)
        paced_fsync = emit_cost(base / "fsync.jsonl", 2_000, True, 500.0)
        e2e = gate_with_audit(base / "gate.jsonl", a.events)
        t0 = time.perf_counter()
        rep = verify(base / "burst.jsonl")
        dt = time.perf_counter() - t0
    doc = {
        "description": "Audit cost on the decision path, durability lag, verify throughput.",
        "parameters": {"events": a.events, "queue_maxsize": 10_000},
        "burst": burst,
        "paced_1000_per_s": paced,
        "paced_500_per_s_fsync": paced_fsync,
        "gate_decide_us": e2e,
        "verify": {
            "records": rep.records,
            "ok": rep.ok,
            "seconds": dt,
            "records_per_s": rep.records / dt if dt else None,
        },
    }
    path = write("audit_overhead", doc)
    for k in ("burst", "paced_1000_per_s", "paced_500_per_s_fsync"):
        r = doc[k]
        lag = r["durable_lag_ms"]
        print(
            f"{k:<22} emit p50={r['emit_us']['p50']:.2f}us p99={r['emit_us']['p99']:.2f}us "
            f"max={r['emit_us']['max']:.1f}us dropped={r['dropped']} "
            f"lag p50={lag['p50']:.2f}ms p99={lag['p99']:.2f}ms max={lag['max']:.1f}ms"
        )
    g = doc["gate_decide_us"]
    print(
        f"decide no audit p50={g['no_audit']['p50']:.2f}us p99={g['no_audit']['p99']:.2f}us; "
        f"with jsonl p50={g['jsonl_audit']['p50']:.2f}us p99={g['jsonl_audit']['p99']:.2f}us "
        f"dropped={g['dropped']}"
    )
    print(f"verify {doc['verify']['records_per_s']:.0f} records/s; wrote {path}")


if __name__ == "__main__":
    main()
