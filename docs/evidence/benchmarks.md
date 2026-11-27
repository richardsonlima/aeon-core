# Benchmarks

Every number below comes from the committed files in [`benchmarks/results/`](https://github.com/richardsonlima/aeon-core/tree/main/benchmarks/results). The tables on this page are generated from those files by `scripts/gen_reference.py`, so they cannot drift from the data.

**These numbers describe one machine only.** Do not read them as a promise for yours. To measure your own: `python benchmarks/run_all.py` (`--quick` for a smoke check). See the [benchmarks README](https://github.com/richardsonlima/aeon-core/blob/main/benchmarks/README.md) for what each benchmark measures and what it does not mean.

<!-- BEGIN GENERATED: machine -->
Machine and run: Apple M1, Darwin 25.6.0, CPython 3.10.21, 8 CPUs; Æon 0.5.0.dev0; run 2026-11-27T14:21:21Z. These numbers describe that machine only.
<!-- END GENERATED: machine -->

## Gate decision latency

One `Gate.decide` call, decision path only, audit off, Python's GC left on so pauses show in p99 and max. Times in µs.

<!-- BEGIN GENERATED: gate -->
µs per `Gate.decide`, audit off, 100000 samples per row (10000 warmup calls excluded).

| Axioms | Mode | Monitor | p50 | p90 | p99 | max |
|---|---|---|---|---|---|---|
| 1 | shadow | on | 11.9 | 12.6 | 13.1 | 135.0 |
| 1 | enforce | on | 11.9 | 12.4 | 13.2 | 195.0 |
| 10 | shadow | on | 14.1 | 14.2 | 15.0 | 81.2 |
| 10 | enforce | on | 14.1 | 14.5 | 15.4 | 80.7 |
| 100 | shadow | on | 35.2 | 36.1 | 38.1 | 117.8 |
| 100 | enforce | on | 35.8 | 36.3 | 38.2 | 133.9 |
| 1 | enforce | off | 11.9 | 12.1 | 12.5 | 53.1 |
<!-- END GENERATED: gate -->

Read the max column. The median is 12 to 36 µs depending on the number of axioms, and single calls in the run took up to 195 µs. Latency also grows with the number of axioms that apply: p99 is 15.0 µs with 10 axioms and 38.1 µs with 100.

## Audit

Cost on the decision path, durability lag and verify speed. "Durable lag" is the time from `emit` to the record being written. "Dropped" is events that did not fit in the 10,000-event queue; each drop is reported later as an `audit.gap` record.

<!-- BEGIN GENERATED: audit -->
| Scenario | emit p50 µs | emit p99 µs | emit max µs | dropped | durable lag p50 ms | lag p99 ms | lag max ms |
|---|---|---|---|---|---|---|---|
| burst of 50000 events, no pause | 2.33 | 3.33 | 76697 | 2081 of 50000 | 55.1 | 137.7 | 199.0 |
| paced 1000/s | 2.50 | 20.71 | 91 | 0 of 5000 | 4.1 | 16.9 | 30.7 |
| paced 500/s with fsync | 2.62 | 21.04 | 30 | 0 of 2000 | 22.3 | 36.0 | 44.8 |

`Gate.decide` without audit: p50 11.8 µs, p99 12.4 µs, max 65 µs. With a JSONL audit log: p50 16.3 µs, p99 438.0 µs, max 3399 µs. Chain verify: 159061 records/s (47921 records).
<!-- END GENERATED: audit -->

The burst row is the unfavourable one: 50,000 events with no pause overran the queue and 2,081 were dropped. At a paced 1,000 events/s none were. One emit in the burst stalled for about 77 ms, most likely from contention with the writer thread. With the audit log on, `Gate.decide` showed a p99 of 438 µs and a worst call of 3.4 ms, against 12.4 µs and 65 µs with it off in the same file: the maxima are noise from the machine and are not reproducible to the digit.

## Detection campaigns

Pre-registered campaigns on the simulated `ops-assistant` scenario: a seeded, scripted agent, **not an LLM**. 30 fault runs and 30 control runs each. Confidence intervals are 95% Wilson intervals.

<!-- BEGIN GENERATED: detection -->
| Campaign | Level | Detection [95% CI] | False positives [95% CI] | Safe State | Harmful actions run | Time to detect (steps p50 / p90 / max) | Hypothesis |
|---|---|---|---|---|---|---|---|
| `broken-schema` (enforce) | ALERT | 100% [89, 100] | 70% [52, 83] | 0% | 0 | 6 / 10 / 13 | NOT supported |
| `conflicting-instructions` (enforce) | BLOCK | 100% [88, 100] | 0% [0, 11] | 97% | 0 | 4 / 13 / 14 | NOT supported |
| `gateway-latency` (enforce) | ALERT | 100% [89, 100] | 67% [49, 81] | 10% | 0 | 1 / 1 / 2 | NOT supported |
| `partial-output` (enforce) | ALERT | 100% [89, 100] | 50% [33, 67] | 3% | 0 | 6 / 10 / 15 | NOT supported |
| `poisoned-output` (enforce) | BLOCK | 96% [82, 99] | 0% [0, 11] | 90% | 0 | 4 / 11 / 24 | NOT supported |
| `rate-limit` (enforce) | LIMIT | 100% [89, 100] | 27% [14, 44] | 27% | 0 | 2 / 5 / 16 | NOT supported |
| `shadow-poisoned-output` (shadow) | BLOCK | 100% [89, 100] | 3% [1, 17] | 0% | 385 | 2 / 13 / 20 | supported |
| `stale-context` (enforce) | ALERT | 97% [83, 99] | 27% [14, 44] | 0% | 0 | 8 / 26 / 32 | NOT supported |
| `tool-timeout` (enforce) | LIMIT | 100% [89, 100] | 20% [10, 37] | 70% | 0 | 2 / 7 / 9 | NOT supported |
<!-- END GENERATED: detection -->

Eight of the nine hypotheses were **not supported**: all eight enforce campaigns, six on false positives (the default budget raises the alarm on 20% to 70% of clean control runs) and two on the Safe State check. The campaigns detect the faults. Detection counts only runs where the fault fired, and "no unapproved destructive action ran" is only evidence in the campaigns where one was attempted. The reports with every unfavourable result are in [`benchmarks/results/campaigns/`](https://github.com/richardsonlima/aeon-core/tree/main/benchmarks/results/campaigns). A worked reading is in [How to read an unfavourable result](../kb/unfavourable-result.md).

## How these relate to claims

[Claims](../claims.md) lists every claim with its status. The ones marked `measured` point at these files, and a claim whose measurement missed its target says so there (`false-positives-10pct`, worst false-positive rate 73%).

## What these benchmarks do not show

- Nothing about a real LLM, a real network or a production agent.
- Nothing about other hardware, other Python versions or other operating systems.
- Nothing about long-running behaviour, memory growth or many concurrent agents.
- The campaign latencies include sleeps in the simulated tools, so they are not gate overhead.
