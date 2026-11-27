# Benchmarks

Every number below comes from the committed files in [`benchmarks/results/`](https://github.com/richardsonlima/aeon-core/tree/main/benchmarks/results). The tables on this page are generated from those files by `scripts/gen_reference.py`, so they cannot drift from the data.

**These numbers describe one machine only.** Do not read them as a promise for yours. To measure your own: `python benchmarks/run_all.py` (`--quick` for a smoke check). See the [benchmarks README](https://github.com/richardsonlima/aeon-core/blob/main/benchmarks/README.md) for what each benchmark measures and what it does not mean.

<!-- BEGIN GENERATED: machine -->
Machine and run: Apple M1, Darwin 25.6.0, CPython 3.12.14, 8 CPUs; Æon 0.5.0.dev0; run 2026-11-27T13:33:14Z. These numbers describe that machine only.
<!-- END GENERATED: machine -->

## Gate decision latency

One `Gate.decide` call, decision path only, audit off, Python's GC left on so pauses show in p99 and max. Times in µs.

<!-- BEGIN GENERATED: gate -->
µs per `Gate.decide`, audit off, 20000 samples per row (2000 warmup calls excluded).

| Axioms | Mode | Monitor | p50 | p90 | p99 | max |
|---|---|---|---|---|---|---|
| 1 | shadow | on | 10.0 | 10.6 | 11.3 | 80.7 |
| 1 | enforce | on | 10.2 | 10.7 | 12.2 | 139.9 |
| 10 | shadow | on | 11.5 | 11.9 | 12.6 | 125.4 |
| 10 | enforce | on | 11.4 | 11.8 | 12.5 | 76.3 |
| 100 | shadow | on | 27.2 | 29.0 | 41.9 | 115.2 |
| 100 | enforce | on | 28.7 | 29.3 | 41.3 | 462.6 |
| 1 | enforce | off | 10.5 | 10.8 | 13.5 | 117.8 |
<!-- END GENERATED: gate -->

Read the max column. The median is about 10 µs, and single calls in the run took up to 462.6 µs. Latency also grows with the number of axioms that apply: p99 is 12.6 µs with 10 axioms and 41.9 µs with 100.

## Audit

Cost on the decision path, durability lag and verify speed. "Durable lag" is the time from `emit` to the record being written. "Dropped" is events that did not fit in the 10,000-event queue; each drop is reported later as an `audit.gap` record.

<!-- BEGIN GENERATED: audit -->
| Scenario | emit p50 µs | emit p99 µs | emit max µs | dropped | durable lag p50 ms | lag p99 ms | lag max ms |
|---|---|---|---|---|---|---|---|
| burst of 20000 events, no pause | 2.12 | 3.29 | 28892 | 3856 of 20000 | 81.7 | 188.2 | 240.2 |
| paced 1000/s | 2.54 | 25.42 | 98 | 0 of 5000 | 4.4 | 12.7 | 44.3 |
| paced 500/s with fsync | 2.88 | 27.00 | 90 | 0 of 2000 | 18.6 | 25.2 | 46.8 |

`Gate.decide` without audit: p50 10.1 µs, p99 42.5 µs, max 5244 µs. With a JSONL audit log: p50 14.4 µs, p99 187.4 µs, max 3711 µs. Chain verify: 179312 records/s (16147 records).
<!-- END GENERATED: audit -->

The burst row is the unfavourable one: 20,000 events with no pause overran the queue and 3,856 were dropped. At a paced 1,000 events/s none were. One emit in the burst stalled for about 29 ms, most likely from contention with the writer thread. With the audit log on, `Gate.decide` showed a p99 of 187 µs and a worst call of 3.7 ms, against 42.5 µs and 5.2 ms with it off in the same file: the maxima in both runs are noise from the machine and are not reproducible.

## Detection campaigns

!!! note "Regenerated at release"
    The committed detection results are from 2026-11-27 and were produced before the detection rate was redefined to count only runs where the fault fired. The tables below are regenerated from `benchmarks/results/` whenever that data is, and the plain-text summary is [`benchmarks/results/summary.md`](https://github.com/richardsonlima/aeon-core/blob/main/benchmarks/results/summary.md).

Pre-registered campaigns on the simulated `ops-assistant` scenario: a seeded, scripted agent, **not an LLM**. 30 fault runs and 30 control runs each. Confidence intervals are 95% Wilson intervals.

<!-- BEGIN GENERATED: detection -->
| Campaign | Level | Detection [95% CI] | False positives [95% CI] | Safe State | Harmful actions run | Time to detect (steps p50 / p90 / max) | Hypothesis |
|---|---|---|---|---|---|---|---|
| `broken-schema` (enforce) | ALERT | 100% [89, 100] | 73% [56, 86] | 0% | 0 | 6 / 10 / 14 | NOT supported |
| `conflicting-instructions` (enforce) | BLOCK | 97% [83, 99] | 0% [0, 11] | 97% | 0 | 4 / 13 / 14 | NOT supported |
| `gateway-latency` (enforce) | ALERT | 100% [89, 100] | 67% [49, 81] | 10% | 0 | 1 / 1 / 2 | NOT supported |
| `partial-output` (enforce) | ALERT | 100% [89, 100] | 50% [33, 67] | 0% | 0 | 5 / 10 / 15 | NOT supported |
| `poisoned-output` (enforce) | BLOCK | 93% [79, 98] | 0% [0, 11] | 93% | 0 | 4 / 20 / 29 | NOT supported |
| `rate-limit` (enforce) | LIMIT | 100% [89, 100] | 27% [14, 44] | 23% | 0 | 2 / 5 / 16 | NOT supported |
| `shadow-poisoned-output` (shadow) | BLOCK | 100% [89, 100] | 3% [1, 17] | 0% | 385 | 2 / 13 / 20 | supported |
| `stale-context` (enforce) | ALERT | 93% [79, 98] | 27% [14, 44] | 0% | 0 | 8 / 19 / 31 | NOT supported |
| `tool-timeout` (enforce) | LIMIT | 100% [89, 100] | 23% [12, 41] | 73% | 0 | 2 / 7 / 9 | NOT supported |
<!-- END GENERATED: detection -->

Seven of the eight hypotheses were **not supported**. The campaigns detect the faults, and in enforce mode no unapproved destructive action ran, but the default budget raises false positives on clean traffic: up to 73%. The reports with every unfavourable result are in [`benchmarks/results/campaigns/`](https://github.com/richardsonlima/aeon-core/tree/main/benchmarks/results/campaigns). A worked reading is in [How to read an unfavourable result](../kb/unfavourable-result.md).

## How these relate to claims

[Claims](../claims.md) lists every claim with its status. The ones marked `measured` point at these files, and a claim whose measurement missed its target says so there (`false-positives-10pct`, worst false-positive rate 73%).

## What these benchmarks do not show

- Nothing about a real LLM, a real network or a production agent.
- Nothing about other hardware, other Python versions or other operating systems.
- Nothing about long-running behaviour, memory growth or many concurrent agents.
- The campaign latencies include sleeps in the simulated tools, so they are not gate overhead.
