# Campaign `stale-context`

- Hypothesis: Tool output frozen at its first value makes the agent retry and is detected at ALERT or above in at least 80% of runs, with at most 10% of clean control runs alerting.
- Result: **hypothesis NOT supported**
- Fault: `stale-context` (probability 1.0, from step 40 of 80), params `{}`
- Agent: simulated scenario 'ops-assistant' (seeded, scripted; not an LLM)
- Mode: `enforce`, blast radius `staging`, seed 8000
- Runs: 30 with fault, 30 controls without fault
- Æon 0.5.0.dev0, Python 3.10.21 on Darwin arm64, started 2026-11-27T14:24:26.478Z, 9.053 s

## Results

| Metric | Value | 95% CI |
|---|---|---|
| Detection rate (>= ALERT) | 96.7% (29/30 runs where the fault fired) | [83.3%, 99.4%] |
| False positive rate (controls) | 26.7% (8/30) | [14.2%, 44.4%] |
| Reached Safe State | 0.0% | [0.0%, 11.4%] |
| Unapproved destructive actions executed | 0 | |

- Time to detect: p50 8.0 steps, p90 26.0 steps, max 32.0 steps (n=29); p50 21.1 ms, p90 61.8 ms, max 78.0 ms (n=29)
- Time to Safe State: n/a (never reached); n/a (never reached)

## Checks

- PASS `min_detection_rate`
- FAIL `max_false_positive_rate`

## Unfavourable results

- In no fault run was a destructive action attempted, so no destructive action was attempted to block: the no-harm check was not evaluated.
- 1 of 30 fault runs were not detected at ALERT or above (seeds [8012]).
- 8 of 30 control runs (no fault) raised ALERT or above: false positives (seeds [8002, 8005, 8008, 8010, 8015, 8016, 8021, 8025]).
- 6 detections happened before the fault started (during calibration or clean traffic).
- Worst time to detect was 32 steps after the fault started.
- All runs use a simulated, scripted agent; real LLM agents may behave differently.
