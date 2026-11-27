# Shadow-first adoption

Adopt in four steps. Each one is reversible, and you move only when the audit log gives you a reason.

| Step | Mode and level | What you do | Move on when |
|---|---|---|---|
| 1. Shadow | `mode = "shadow"` | Wrap executors with `enforce`. Nothing is stopped; every decision and verdict is recorded. | You have read real traffic in `aeon audit tail` and know which axioms fire, and how often. |
| 2. `ALERT` | shadow or enforce, rules at `ALERT` | Rules record but never interfere. Tune them until the alerts are worth reading. | The alert rate is low enough that a human would look at each one. |
| 3. `LIMIT` | `enforce`, rules at `LIMIT` | Risky actions need an approval. Wire an approver or `Action.approved`. | Approvals are rare and the approvers keep up. |
| 4. `BLOCK` | `enforce`, a few rules at `BLOCK` | Only rules you trust and can explain: destructive tools, exfiltration patterns. | You accept that a blocked agent enters [Safe State](safe-state.md) until someone resets it. |

New installs start in shadow mode, and `aeon init` writes `mode = "shadow"`.

## Why this order

An axiom is code you wrote about what is safe. The first time it meets real traffic it will be wrong somewhere. In shadow mode a wrong rule costs a log line. In `BLOCK` it stops an agent. The [budget](budget.md) is worse: its defaults gave false-positive rates of up to 70% on the simulated agent (see the [blog post](../blog/first-unfavourable-result.md)), so run it at `ALERT` first and calibrate.

Shadow mode also shows what you would have caught. In the committed shadow campaign, 385 unapproved destructive actions ran across 30 fault runs while the gate recorded a `BLOCK` for each. That is the number shadow mode prevents you from guessing.

## What shadow does not protect

In shadow mode nothing is stopped, by design, except the kill-switch. If you need protection from day one, shadow is not it. Start with a small `deny_tools` list at `BLOCK` for the tools you would never want unreviewed, and keep everything else in shadow.

Guides: [Roll out in shadow mode](../guides/shadow-rollout.md). KB: [Why shadow first](../kb/why-shadow-first.md).
