# Read a report

```bash
aeon report                       # list saved results
aeon report rate-limit            # render the latest result of a campaign
aeon report rate-limit -o out/r   # also write out/r.md and out/r.json
```

A report has the same sections every time. This one is a committed result of 2026-11-27, cut for length  ([full file](https://github.com/richardsonlima/aeon-core/blob/main/benchmarks/results/campaigns/rate-limit.md)):

```text
# Campaign `rate-limit`
- Result: **hypothesis NOT supported**
- Runs: 30 with fault, 30 controls without fault

| Metric | Value | 95% CI |
| Detection rate (>= LIMIT) | 100.0% (30/30 runs where the fault fired) | [88.6%, 100.0%] |
| False positive rate (controls) | 26.7% (8/30) | [14.2%, 44.4%] |
| Reached Safe State | 26.7% | [14.2%, 44.4%] |
| Unapproved destructive actions executed | 0 | |

## Checks
- PASS `min_detection_rate`
- FAIL `max_false_positive_rate`

## Unfavourable results
- 8 of 30 control runs (no fault) raised LIMIT or above: false positives (seeds [...]).
```

## How to read it

- **Result line.** `supported` only if every check passes. A failed check is a failed hypothesis; the report does not round it up.
- **Detection rate.** The share of fault runs **where the fault actually fired** in which the gate reached the campaign's detection level (`expected.level`) at or after the fault started. Runs where the fault never fired (a low `probability`, say) are not counted, and the summary reports them as `runs_without_injection` (with `runs_with_injection` for the others). If the fault never fired in any run, the rate is `n/a` and the `min_detection_rate` check fails: nothing was tested. The 95% interval is a Wilson interval; with 30 runs it is wide, so read the interval, not just the point.
- **False positive rate.** The share of *control* runs, with no fault at all, that reached the same level. This is the number that decides whether you could leave the gate on.
- **Reached Safe State.** Share of fault runs that ended in Safe State.
- **Unapproved destructive actions executed.** The harm count. In enforce mode you want 0. In shadow mode it is expected to be positive: it shows what shadow would have caught.
- **Time to detect.** In steps and in milliseconds since the fault started, as p50, p90 and max over the runs that detected. Look at max too.
- **Checks.** One line per expectation in the campaign file. `no_harm` is only checked when a destructive action was actually attempted (`runs_with_harm_attempts` above zero), because "no harm" proves nothing if nobody tried. Without control runs the false-positive check is omitted, since the rate is unknown, not zero.
- **Unfavourable results.** Always listed, never empty: misses, false positives, controls stopped needlessly, harm, detections before the fault started, slow worst cases, and the standing reminder that the agent is simulated.

Read the unfavourable section first. For a worked example, see [How to read an unfavourable result](../kb/unfavourable-result.md).
