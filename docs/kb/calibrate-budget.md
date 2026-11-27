# How to calibrate a budget

The [budget](../concepts/budget.md) needs numbers that fit your agent. The defaults (`slack 1.0`, `alert_at 5`, `limit_at 10`, `block_at 20`, `baseline_n 50`) are not a recommendation: on the simulated agent they produced high false-positive rates. Calibrate against your own clean traffic.

## Procedure

1. **Collect a clean baseline period in shadow.** The budget needs `baseline_n` results per agent before it scores anything. Calibrate during normal operation. A baseline taken during an incident makes the incident look normal.
2. **Watch the score on clean traffic.** `GET /v1/status` (or `aeon_status`, or `Gate.status()`) reports per agent `calibrated`, `deviation`, `accumulated`, `max_accumulated` and `level`. On clean traffic, `max_accumulated` is how high the CUSUM wandered with nothing wrong.
3. **Set thresholds above that, with margin.** `alert_at` should sit above the largest `max_accumulated` you saw on clean traffic. Then spread `limit_at` and `block_at` further up.
4. **Raise `slack` if the score drifts upward on clean traffic.** `S` gains `d_t - slack` each step. If the average clean `d_t` is close to `slack`, `S` wanders. Raising `slack` makes it drain.
5. **Use the envelope for hard limits.** `p99_ms`, `error_rate`, `max_cost`, `max_tokens` need no calibration. Set `p99_ms` from the p99 you observed with margin, and remember the window (default 50) is small, so a p99 over 50 samples is close to the maximum.
6. **Validate with controls.** Write a [campaign](../guides/campaigns.md) with control runs and a `max_false_positive_rate` you accept, and run it with `--runs 30 --controls 30` or more.
7. **Re-register after tuning.** If you change the budget because a campaign failed, the old result no longer counts. Write the new thresholds into the campaign file before you run it again.

## What I saw on the simulated agent

An exploratory run on the `broken-schema` campaign, 30 controls each time, same seeds. It is **not** a result: I tuned on the same scenario I measured on, and the scenario is not an LLM. It only shows which knobs matter.

| Budget | Detection | False positives on controls |
|---|---|---|
| `baseline_n = 30` (the campaign's setting) | 100% | 67% (20 of 30) |
| `baseline_n = 50` | 100% | 27% (8 of 30) |
| `baseline_n = 30`, `slack = 2.0` | 100% | 3% (1 of 30) |
| `baseline_n = 30`, `slack = 2.0`, thresholds doubled | 90% | 0% (0 of 30) |

Two things to notice. A longer baseline helped a lot, because 30 samples of a very steady agent give a poor estimate of its spread. And the first row, 20 of 30, differs slightly from the committed result for the same campaign, 21 of 30 (an earlier run gave 22): the simulated agent sleeps for a few milliseconds per call, so latency-based outcomes move between runs even with fixed seeds.

## Pitfalls

- A baseline of exactly zero errors makes one error a z of 10. That is correct for an agent that never fails and noisy for one that sometimes does.
- Very fast agents (sub-millisecond latency) hit the 1 ms floor on the latency spread, so most of the latency term comes from the floor, not from your data.
- `reset` after Safe State clears the window and totals, so p99 and error-rate checks go quiet until `min_samples` results arrive again.
