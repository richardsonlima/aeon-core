# Why shadow first

**Short answer:** a rule you have not watched on real traffic is a guess, and in `BLOCK` a wrong guess stops a working agent.

## What shadow mode does

In `shadow` mode the gate runs every axiom and the budget, records the verdict and the reasons in the audit log, and lets the action run. The one exception is the kill-switch, which is enforced in every mode. New installs and `aeon init` start in shadow.

## What the repository's own numbers say

- **Rules and budgets misfire.** With the default budget, clean control runs of the simulated agent raised an alarm in 23% to 73% of runs in six of the eight campaigns (see [How to read an unfavourable result](unfavourable-result.md)). If those had been `BLOCK`, the agent would have been stopped for no reason. In shadow they are log lines.
- **Shadow shows the exposure.** In the committed shadow campaign, 385 unapproved destructive actions ran across 30 fault runs while the gate recorded a `BLOCK` for each of them, and its false-positive rate on controls was 3.3% (1 of 30). You learn what you would have caught before you let it act.
- **It has a cost you should know.** Shadow does not protect. Those 385 actions ran. If a tool must never run unreviewed, put a small `BLOCK` rule on it from day one and keep the rest in shadow.

## What to look at while in shadow

1. Which axioms fire, how often, on which tools (`aeon audit tail --type decision`).
2. For each `BLOCK` verdict, would stopping have been right?
3. How the budget behaves: calibration progress, `accumulated` and `max_accumulated` per agent from `GET /v1/status` or `aeon_status`.
4. Whether `audit.gap` records appear (your event rate exceeds the queue) or `audit.backend_error` (storage failed).

## When to move on

Move one rule at a time, when the log shows the rule's verdicts were right and the false positives are at a level you accept. The order is `ALERT`, `LIMIT`, `BLOCK`. See [Shadow-first adoption](../concepts/shadow-first.md) and [Roll out in shadow mode](../guides/shadow-rollout.md).

## Caveat

There is no field data yet. Nobody, including me, has run Æon in shadow on a production agent and reported results. The reasoning here comes from the simulated campaigns and from how the gate works, not from production experience. See the [method post](../blog/shadow-mode-method.md).
