"""Gate decision latency: Gate.decide per call, for 1, 10 and 100 axioms.

Each sample times one decide() with perf_counter_ns. Warmup calls are excluded. The
audit sink is off so this measures the decision path alone (see bench_audit for the
cost of emitting). Python's GC stays enabled, so pauses show up in p99 and max.
"""

from __future__ import annotations

import argparse
import time

from _common import summarize, write

from aeon.axioms import Action, AxiomSpec, Gate, Level
from aeon.baseline import Monitor


def make_gate(n: int, mode: str, with_monitor: bool) -> Gate:
    specs = [
        AxiomSpec(f"r{i}", (lambda k: lambda a: a.tool != f"never{k}")(i), Level.BLOCK)
        for i in range(n)
    ]
    return Gate(specs, mode=mode, monitor=Monitor() if with_monitor else None)


def measure(n_axioms: int, mode: str, samples: int, warmup: int, monitor: bool) -> dict:
    g = make_gate(n_axioms, mode, monitor)
    act = Action("read_file", {"path": "/tmp/x"})
    for _ in range(warmup):
        g.decide(act)
    ns = []
    clock = time.perf_counter_ns
    for _ in range(samples):
        t0 = clock()
        g.decide(act)
        ns.append(clock() - t0)
    us = [x / 1e3 for x in ns]
    return {"axioms": n_axioms, "mode": mode, "monitor": monitor, "latency_us": summarize(us)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=100_000)
    ap.add_argument("--warmup", type=int, default=10_000)
    a = ap.parse_args()
    rows = []
    for n in (1, 10, 100):
        for mode in ("shadow", "enforce"):
            rows.append(measure(n, mode, a.samples, a.warmup, monitor=True))
    rows.append(measure(1, "enforce", a.samples, a.warmup, monitor=False))
    path = write(
        "gate_latency",
        {
            "description": "Latency of one Gate.decide call (decision path only, audit off).",
            "parameters": {
                "samples": a.samples,
                "warmup_excluded": a.warmup,
                "action": "read_file, every axiom passes",
            },
            "rows": rows,
        },
    )
    for r in rows:
        s = r["latency_us"]
        print(
            f"axioms={r['axioms']:>3} {r['mode']:<7} monitor={r['monitor']!s:<5} "
            f"p50={s['p50']:.2f}us p90={s['p90']:.2f}us p99={s['p99']:.2f}us max={s['max']:.1f}us"
        )
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
