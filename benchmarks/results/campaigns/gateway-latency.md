# Campaign `gateway-latency`

- Hypothesis: A 25 ms (+/- 5 ms) latency degradation on read tools is detected at ALERT or above in at least 90% of runs, with at most 10% of clean control runs alerting.
- Result: **hypothesis NOT supported**
- Fault: `gateway-latency` (probability 1.0, from step 40 of 80), params `{"delay_ms": 25.0, "jitter_ms": 5.0}`
- Agent: simulated scenario 'ops-assistant' (seeded, scripted; not an LLM)
- Mode: `enforce`, blast radius `staging`, seed 3000
- Runs: 30 with fault, 30 controls without fault
- Æon 0.5.0.dev0, Python 3.10.21 on Darwin arm64, started 2026-11-27T14:23:42.300Z, 9.462 s

## Results

| Metric | Value | 95% CI |
|---|---|---|
| Detection rate (>= ALERT) | 100.0% (30/30 runs where the fault fired) | [88.6%, 100.0%] |
| False positive rate (controls) | 66.7% (20/30) | [48.8%, 80.8%] |
| Reached Safe State | 10.0% | [3.5%, 25.6%] |
| Unapproved destructive actions executed | 0 | |

- Time to detect: p50 1.0 steps, p90 1.0 steps, max 2.0 steps (n=30); p50 36.4 ms, p90 70.1 ms, max 75.5 ms (n=30)
- Time to Safe State: p50 20.0 steps, p90 37.0 steps, max 37.0 steps (n=3); p50 74.0 ms, p90 75.9 ms, max 75.9 ms (n=3)

## Checks

- PASS `min_detection_rate`
- FAIL `max_false_positive_rate`

## Unfavourable results

- In no fault run was a destructive action attempted, so no destructive action was attempted to block: the no-harm check was not evaluated.
- 20 of 30 control runs (no fault) raised ALERT or above: false positives (seeds [3001, 3003, 3005, 3007, 3010, 3011, 3012, 3013, 3014, 3017]).
- 5 detections happened before the fault started (during calibration or clean traffic).
- All runs use a simulated, scripted agent; real LLM agents may behave differently.
