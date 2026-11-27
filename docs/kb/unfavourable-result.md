# How to read an unfavourable result

!!! note "How the numbers are counted"
    Detection counts only the fault runs where the fault actually fired. `no_harm` is checked only when a destructive action was attempted, and the false-positive check is omitted without controls (see [Read a report](../guides/reports.md)). Figures are the committed results of 2026-11-27; the plain-text summary is [`benchmarks/results/summary.md`](https://github.com/richardsonlima/aeon-core/blob/main/benchmarks/results/summary.md).

A worked example from the committed campaign results (Æon 0.5.0.dev0, Apple M1, Python 3.10.21, 2026-11-27, simulated agent, 30 fault runs and 30 control runs per campaign, default budget with `baseline_n = 30`).

## The results

| Campaign | Detection (>= level), runs where the fault fired | False positives on clean controls | Hypothesis |
|---|---|---|---|
| `broken-schema` (ALERT) | 100% (30/30) | **70.0% (21/30)**, CI [52.1%, 83.3%] | not supported |
| `gateway-latency` (ALERT) | 100% (30/30) | **66.7% (20/30)**, CI [48.8%, 80.8%] | not supported |
| `partial-output` (ALERT) | 100% (30/30) | **50.0% (15/30)**, CI [33.2%, 66.8%] | not supported |
| `stale-context` (ALERT) | 96.7% (29/30) | **26.7% (8/30)**, CI [14.2%, 44.4%] | not supported |
| `rate-limit` (LIMIT) | 100% (30/30) | **26.7% (8/30)**, CI [14.2%, 44.4%] | not supported |
| `tool-timeout` (LIMIT) | 100% (30/30) | **20.0% (6/30)**, CI [9.5%, 37.3%] | not supported |
| `poisoned-output` (BLOCK) | 96.4% (27/28) | 0% (0/30) | not supported (3 runs did not reach Safe State, none had attempted a destructive action) |
| `conflicting-instructions` (BLOCK) | 100% (29/29) | 0% (0/30) | not supported (1 run did not reach Safe State, and the fault never fired in it) |
| `shadow-poisoned-output` (BLOCK, shadow) | 100% (30/30) | 3.3% (1/30) | supported |

The targets were at most 10% false positives. All eight enforce campaigns missed their hypothesis: six on the false-positive check, two on the Safe State check. Detection outcomes also vary slightly between reruns with the same seeds (the latest rerun of `poisoned-output` shows 3 runs without Safe State, all with no destructive attempt).

## How to read it, step by step

1. **Start with the unfavourable section of the report.** It is never empty. Here it lists the false positives with their seeds, the control runs stopped needlessly (1 in `partial-output`), the detections that happened before the fault started (2 to 7 in four of the campaigns), and the slow worst cases (up to 32 steps to detect in `stale-context`).
2. **Compare detection with false positives.** A detection rate of 100% means little next to a 70% false-positive rate: an alarm that fires on clean traffic three times in four is not detecting, it is firing. The two numbers have to be read together.
3. **Use the intervals.** With 30 runs, 21/30 has a 95% interval of [52.1%, 83.3%]. Even the best end is far above the 10% target. The result is not a small-sample fluke.
4. **Look at harm separately.** Where a destructive action was attempted (`poisoned-output`, `conflicting-instructions`), 0 unapproved destructive actions ran: the gate's `BLOCK` rule on destructive tools worked. In the other six enforce campaigns none was attempted, so the report says the no-harm check was not evaluated. The part that failed was the budget's alarm, not the rule. Do not let one number hide the other.
5. **Ask what the simulated agent is.** Latency here is a few milliseconds of sleep with jitter. Real agents differ, so a rate measured here does not transfer. What does transfer is the mechanism.

## Why it happens

I looked at clean control runs of `broken-schema` and traced the monitor. The calibrated baseline of a very steady agent looked like this (seeds 7000 and 7002): latency mean about 1.7 to 1.8 ms, std about 0.7 to 0.8 ms, error rate 0, repeat rate 0.13 to 0.2. With a latency spread that small, ordinary jitter gives a latency z near 1. The one-sided clip keeps the positive half of the noise, which averages about 0.4 per step, the repeat term fires whenever the agent happens to re-read something (z of about 2.5 when the baseline repeat rate is 0.13), and the drift term adds a little. The expected step score on clean traffic ends up close to `slack = 1.0`. With the CUSUM `S = max(0, S + d - 1)` that means a random walk with almost no drift, which wanders up and crosses `alert_at = 5` within the 50 scored steps in many runs. The observed first alerts were at accumulated 5.3 and 6.1 with step scores of 1.4 and 3.4.

That explanation is my reading of the traces, not a proof. What I did verify: raising `slack` to 2.0 took the false positives on the same campaign from 20 of 30 to 1 of 30 in a rerun, and a longer baseline (50) took it to 8 of 30 (see [How to calibrate a budget](calibrate-budget.md), where the caveat about tuning on the same scenario applies).

## What to do with a result like this

- Do not raise thresholds until the table goes green. Understand the cause, change the thing that causes it, write the new setting into the campaign file, and run again.
- Keep the old result. It is the baseline for the next one. The repository keeps both the reports and the raw JSON.
- In production terms: run the budget at `ALERT` in shadow until its false-positive rate on your own clean traffic is something you would accept at `BLOCK`.

Next: the [blog post](../blog/first-unfavourable-result.md) on this result, and [Known limits](../known-limits.md).
