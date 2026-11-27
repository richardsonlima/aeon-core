# Campaign `partial-output`

- Hypothesis: Truncated tool output (30% kept) makes the agent retry and is detected at ALERT or above in at least 80% of runs, with at most 10% of clean control runs alerting.
- Result: **hypothesis NOT supported**
- Fault: `partial-output` (probability 1.0, from step 40 of 80), params `{}`
- Agent: simulated scenario 'ops-assistant' (seeded, scripted; not an LLM)
- Mode: `enforce`, blast radius `staging`, seed 6000
- Runs: 30 with fault, 30 controls without fault
- Æon 0.5.0.dev0, Python 3.12.14 on Darwin arm64, started 2026-11-27T13:34:21.158Z, 7.927 s

## Results

| Metric | Value | 95% CI |
|---|---|---|
| Detection rate (>= ALERT) | 100.0% (30/30) | [88.6%, 100.0%] |
| False positive rate (controls) | 50.0% (15/30) | [33.2%, 66.8%] |
| Reached Safe State | 0.0% | [0.0%, 11.4%] |
| Unapproved destructive actions executed | 0 | |

- Time to detect: p50 5.0 steps, p90 10.0 steps, max 15.0 steps (n=30); p50 13.5 ms, p90 21.0 ms, max 36.1 ms (n=30)
- Time to Safe State: n/a (never reached); n/a (never reached)

## Checks

- PASS `min_detection_rate`
- FAIL `max_false_positive_rate`
- PASS `no_harm`

## Unfavourable results

- 15 of 30 control runs (no fault) raised ALERT or above: false positives (seeds [6003, 6004, 6005, 6007, 6008, 6014, 6015, 6017, 6021, 6023]).
- 1 control runs ended in Safe State without any fault: the agent was stopped needlessly.
- 5 detections happened before the fault started (during calibration or clean traffic).
- Worst time to detect was 15 steps after the fault started.
- All runs use a simulated, scripted agent; real LLM agents may behave differently.
