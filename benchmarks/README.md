# Benchmarks

Three benchmarks, one runner. Results are committed in [`results/`](results/), and the docs render them on the [Benchmarks page](https://www.richardsonlima.com.br/aeon/docs/evidence/benchmarks/).

## Reproduce

```bash
uv sync --group dev --extra runtime        # or: pip install -e ".[runtime]"
python benchmarks/run_all.py               # full run, a few minutes
python benchmarks/run_all.py --quick       # fewer samples, a smoke check
```

`run_all.py` runs the three scripts below, writes `results/summary.md`, then regenerates `docs/claims.yaml` through `scripts/claims.py`. Each script writes one JSON file to `results/` with the machine description, the parameters and the raw distribution (p50, p90, p99, max). The campaigns also write per-campaign reports to `results/campaigns/`. Close other work while it runs, and expect different numbers on your machine.

## What each one measures, and what it does not mean

| Script | Measures | Does **not** mean |
|---|---|---|
| `bench_gate.py` | Latency of one `Gate.decide`, decision path only, audit off, for 1, 10 and 100 axioms, in shadow and enforce mode, GC left on. | The cost of a real agent step, which includes a model call thousands of times slower. Axioms here are trivial lambdas; a slow axiom of yours is not included. |
| `bench_audit.py` | Cost of `emit` on the decision path, time until a record is durable, verify speed, and how many events are dropped in a burst, with and without `fsync`. | Throughput on your disk. The burst test overruns the 10,000-event queue on purpose to show the drop behaviour. |
| `bench_detection.py` | Pre-registered campaigns (`campaigns/*.toml`) on a simulated, scripted agent: detection rate, false positives on control runs, time to detect, harm. | Detection of a real LLM agent. The simulated tools sleep a few milliseconds, so latency-based results move between runs even with fixed seeds. |

## The machine caveat

The committed results come from one machine: Apple M1, 8 CPUs, macOS (Darwin 25.6.0), CPython 3.12.14, Æon 0.5.0.dev0, run on 2026-11-27. **These numbers describe that machine only.** Latency maxima in particular are noise from the scheduler and the garbage collector, and do not reproduce.

## Unfavourable results

Generated from the committed result files by `scripts/gen_reference.py`. Nothing here is hidden or rounded.

<!-- BEGIN GENERATED: unfavourable -->
| Benchmark | Result | Why it matters |
|---|---|---|
| gate_latency | Worst single decision 195 µs (1 axioms, enforce), against a p50 of 11.9 µs | Rare spikes (GC, scheduler) are real. Read p99 and max, not the median alone. |
| gate_latency | p99 grows from 13.2 µs (1 axiom) to 38.2 µs (100 axioms) | Cost is linear in the number of axioms that apply to a tool. |
| audit_overhead | Burst of 50000 events with no pause: 2081 dropped (4.2%), recorded as `audit.gap` | The queue is bounded on purpose so the decision path never waits. A burst above its size loses events, and the log says so. |
| audit_overhead | Emit max 76697 µs in the burst, durable lag p99 138 ms, max 199 ms | One emit stalled for about 77 ms, most likely the writer thread holding the GIL. |
| audit_overhead | `Gate.decide` with JSONL audit on: p99 438 µs, max 3399 µs (without audit: p99 12 µs, max 65 µs) | Turning audit on adds tail latency from the writer thread sharing the GIL. |
| detection / broken-schema | False positives 70% (21 of 30 clean controls) at ALERT; target was at most 10% | The default budget fires on clean traffic of the simulated agent. |
| detection / gateway-latency | False positives 67% (20 of 30 clean controls) at ALERT; target was at most 10% | The default budget fires on clean traffic of the simulated agent. |
| detection / partial-output | False positives 50% (15 of 30 clean controls) at ALERT; target was at most 10% | The default budget fires on clean traffic of the simulated agent. |
| detection / rate-limit | False positives 27% (8 of 30 clean controls) at LIMIT; target was at most 10% | The default budget fires on clean traffic of the simulated agent. |
| detection / stale-context | False positives 27% (8 of 30 clean controls) at ALERT; target was at most 10% | The default budget fires on clean traffic of the simulated agent. |
| detection / tool-timeout | False positives 20% (6 of 30 clean controls) at LIMIT; target was at most 10% | The default budget fires on clean traffic of the simulated agent. |
| detection / poisoned-output | Detection 96%: 1 of 30 fault runs missed at BLOCK | A fault the gate did not contain in every run. See the campaign report. |
| detection / stale-context | Detection 97%: 1 of 30 fault runs missed at ALERT | A fault the gate did not contain in every run. See the campaign report. |
| detection / shadow-poisoned-output | 385 unapproved destructive actions executed (shadow mode) | Expected in shadow mode: it records and never blocks. This is what shadow would have caught. |
| detection | 8 of 9 pre-registered hypotheses not supported | Not supported: `broken-schema`, `conflicting-instructions`, `gateway-latency`, `partial-output`, `poisoned-output`, `rate-limit`, `stale-context`, `tool-timeout`. |
<!-- END GENERATED: unfavourable -->

## Adding a benchmark

Write the result to `results/<name>.json` through `_common.write`, add it to `run_all.py`, and, if it supports a claim, add a measurement to `scripts/claims.py`. A claim whose measurement misses its target stays `implemented` and carries a note saying so.
