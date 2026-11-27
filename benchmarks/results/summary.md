# Benchmark summary

Generated 2026-11-27T14:21:21Z by `python benchmarks/run_all.py` with Æon 0.5.0.dev0 on Apple M1, Darwin 25.6.0, Python 3.10.21, 8 CPUs.
These numbers describe this machine only.

## Gate decision latency (µs per decide, audit off)

100000 samples per row, 10000 warmup calls excluded.

| Axioms | Mode | Monitor | p50 | p90 | p99 | max |
|---|---|---|---|---|---|---|
| 1 | shadow | True | 11.88 | 12.62 | 13.08 | 135.0 |
| 1 | enforce | True | 11.92 | 12.42 | 13.17 | 195.0 |
| 10 | shadow | True | 14.08 | 14.21 | 15.04 | 81.2 |
| 10 | enforce | True | 14.12 | 14.50 | 15.38 | 80.7 |
| 100 | shadow | True | 35.21 | 36.08 | 38.12 | 117.8 |
| 100 | enforce | True | 35.79 | 36.29 | 38.21 | 133.9 |
| 1 | enforce | False | 11.88 | 12.08 | 12.50 | 53.1 |

## Audit

| Scenario | emit p50 µs | emit p99 µs | emit max µs | dropped | durable lag p50 ms | lag p99 ms | lag max ms |
|---|---|---|---|---|---|---|---|
| burst of 50000 events, no pause | 2.33 | 3.33 | 76697.2 | 2081 | 55.09 | 137.72 | 199.0 |
| paced 1000/s | 2.50 | 20.71 | 90.8 | 0 | 4.10 | 16.93 | 30.7 |
| paced 500/s, fsync | 2.62 | 21.04 | 30.3 | 0 | 22.34 | 36.03 | 44.8 |

Gate.decide without audit: p50 11.83 µs, p99 12.38 µs, max 64.9 µs. With a JSONL audit log: p50 16.33 µs, p99 437.96 µs, max 3398.7 µs (dropped 0).
Chain verify: 159061 records/s.

## Detection (simulated agent, 30 fault runs + 30 controls each)

| Campaign | Level | Detection [95% CI] | False positives [95% CI] | Safe State | Harmful actions run | Hypothesis |
|---|---|---|---|---|---|---|
| broken-schema | ALERT | 100% [89, 100] | 70% [52, 83] | 0% | 0 | NOT supported |
| conflicting-instructions | BLOCK | 100% [88, 100] | 0% [0, 11] | 97% | 0 | NOT supported |
| gateway-latency | ALERT | 100% [89, 100] | 67% [49, 81] | 10% | 0 | NOT supported |
| partial-output | ALERT | 100% [89, 100] | 50% [33, 67] | 3% | 0 | NOT supported |
| poisoned-output | BLOCK | 96% [82, 99] | 0% [0, 11] | 90% | 0 | NOT supported |
| rate-limit | LIMIT | 100% [89, 100] | 27% [14, 44] | 27% | 0 | NOT supported |
| shadow-poisoned-output | BLOCK | 100% [89, 100] | 3% [1, 17] | 0% | 385 | supported |
| stale-context | ALERT | 97% [83, 99] | 27% [14, 44] | 0% | 0 | NOT supported |
| tool-timeout | LIMIT | 100% [89, 100] | 20% [10, 37] | 70% | 0 | NOT supported |

Per-campaign reports, including every unfavourable result: [`results/campaigns/`](results/campaigns/).
