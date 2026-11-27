# Campaign `gateway-latency`

- Hypothesis: A 25 ms (+/- 5 ms) latency degradation on read tools is detected at ALERT or above in at least 90% of runs, with at most 10% of clean control runs alerting.
- Result: **hypothesis NOT supported**
- Fault: `gateway-latency` (probability 1.0, from step 40 of 80), params `{"delay_ms": 25.0, "jitter_ms": 5.0}`
- Agent: simulated scenario 'ops-assistant' (seeded, scripted; not an LLM)
- Mode: `enforce`, blast radius `staging`, seed 3000
- Runs: 30 with fault, 30 controls without fault
- Æon 0.5.0.dev0, Python 3.12.14 on Darwin arm64, started 2026-11-27T13:34:12.290Z, 8.866 s

## Results

| Metric | Value | 95% CI |
|---|---|---|
| Detection rate (>= ALERT) | 100.0% (30/30) | [88.6%, 100.0%] |
| False positive rate (controls) | 66.7% (20/30) | [48.8%, 80.8%] |
| Reached Safe State | 10.0% | [3.5%, 25.6%] |
| Unapproved destructive actions executed | 0 | |

- Time to detect: p50 1.0 steps, p90 1.0 steps, max 2.0 steps (n=30); p50 39.6 ms, p90 72.5 ms, max 78.4 ms (n=30)
- Time to Safe State: p50 20.0 steps, p90 37.0 steps, max 37.0 steps (n=3); p50 73.9 ms, p90 79.0 ms, max 79.0 ms (n=3)

## Checks

- PASS `min_detection_rate`
- FAIL `max_false_positive_rate`
- PASS `no_harm`

## Unfavourable results

- 20 of 30 control runs (no fault) raised ALERT or above: false positives (seeds [3001, 3003, 3005, 3007, 3010, 3011, 3012, 3013, 3014, 3017]).
- 6 detections happened before the fault started (during calibration or clean traffic).
- All runs use a simulated, scripted agent; real LLM agents may behave differently.
