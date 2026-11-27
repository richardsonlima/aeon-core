# The first unfavourable result

!!! note "Draft for review"
    Not published. Written by Richardson Lima.

!!! note "Numbers in this post"
    The campaign numbers are from the committed results of 2026-11-27 (Apple M1, Python 3.12.14). They were produced before the detection rate was redefined to count only runs where the fault fired (see [Read a report](../guides/reports.md)), and they are regenerated at release. The current figures are always in [`benchmarks/results/summary.md`](https://github.com/richardsonlima/aeon-core/blob/main/benchmarks/results/summary.md). Read the method here, not the digits.

I pre-registered eight chaos campaigns: hypothesis, fault, expected outcome and thresholds, committed before the results. Then I ran them. Seven of eight did not meet their hypothesis. This is what happened.

## The numbers

Simulated agent, 30 fault runs and 30 control runs (no fault) per campaign, default budget, one machine (Apple M1, Python 3.12.14, 2026-11-27). The target was at most 10% false positives.

| Campaign | Detection | False positives on clean controls |
|---|---|---|
| `broken-schema` | 100% | 73.3% (22/30) |
| `gateway-latency` | 100% | 66.7% (20/30) |
| `partial-output` | 100% | 50.0% (15/30) |
| `stale-context` | 93.3% | 26.7% (8/30) |
| `rate-limit` | 100% | 26.7% (8/30) |
| `tool-timeout` | 100% | 23.3% (7/30) |
| `poisoned-output` | 93.3% | 0% (0/30) |
| `conflicting-instructions` | 96.7% | 0% (0/30) |

In enforce mode, **no unapproved destructive action ran** in any campaign. The two `BLOCK`-level campaigns missed because detection was 93.3% and 96.7% against a bar of "every run" or 95%.

## What it means

The detection numbers look great and mean little. A budget alarm that fires on three of four clean runs is not detecting a fault, it is firing. Detection and false positives have to be read together, and I printed them in the same table for that reason.

The part that held was the rule: `no_destructive_tool_call` blocked every unapproved destructive action. The part that failed was the budget's behavioural alarm.

## Why

I traced the monitor on clean runs. The simulated agent is very steady (latency about 1.7 ms, spread about 0.7 ms, no errors), so the baseline built from 30 samples is tight. On clean traffic the expected step score ended up close to the CUSUM slack of 1.0, which makes the accumulated score a random walk with almost no drift, and over 50 scored steps it crosses the alert threshold in many runs. That is my reading of the traces. What I checked: raising the slack to 2.0 cut false positives on `broken-schema` from 20 of 30 to 1 of 30 in a rerun, and a baseline of 50 instead of 30 cut it to 8 of 30. I tuned on the same scenario I measured, so those are not results. They only say where the problem is.

A second finding came free: my rerun of the default gave 20 of 30, the committed run gave 22 of 30. Same seeds. The simulated tools sleep for milliseconds, so latency-based outcomes move.

## What is next

1. Fix the cause, not the table. Candidates: a larger default baseline, a larger default slack, or a spread floor that reflects a real agent instead of a sleeping simulation. Each change gets written into the campaign files **before** I rerun them.
2. Keep this result in the repository, with its raw JSON, as the number to beat.
3. Run the same campaigns against a real model, where I expect the picture to differ, and say so either way.
4. Until then the claim `false-positives-10pct` stays `implemented` with the note "target not met", and shadow mode stays the recommended start.

Read more: [How to read an unfavourable result](../kb/unfavourable-result.md), [How to calibrate a budget](../kb/calibrate-budget.md), [Benchmarks](../evidence/benchmarks.md).
