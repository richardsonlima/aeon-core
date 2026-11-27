# Gate and observation path

Æon splits its work in two paths on purpose.

| | Decision path | Observation path |
|---|---|---|
| Question | May this action run, right now? | What happened, and is the agent drifting? |
| Code | `Gate.decide` | `Gate.observe`, `Monitor.record`, `AuditLog` writer thread |
| Runs | synchronously, in the caller's thread | after the action, and on a background thread for audit |
| Allowed to do | read memory, call your axiom functions, read a cached budget level | hash, write files, compute baselines, update metrics |
| Never does | I/O, network, waiting on a lock held by the observation path | block the decision path |

## The decision path

`Gate.decide(action)` never raises and uses only the standard library. For one action it does this, in order:

1. If the **kill-switch** is engaged, add a `BLOCK` finding.
2. If the agent is in **Safe State** and the gate is in `enforce` mode, add a `BLOCK` finding.
3. Run every axiom that applies to the tool. An axiom returns `True` or `None` to pass, `False` or a reason string to object at its declared level, or a `Violation` to pick the level per call. An axiom that raises counts as a `BLOCK` finding.
4. Read the **cached** budget level of the agent from the `Monitor` (no computation here) and add a finding if it is above `GO`.
5. The verdict is the highest level among the findings (`GO` if none).

What the verdict does depends on the mode:

| Mode | `GO`, `ALERT` | `LIMIT` | `BLOCK` |
|---|---|---|---|
| `shadow` | runs | runs, verdict recorded | runs, verdict recorded |
| `enforce` | runs | runs only if the action is `approved` or the approver hook says yes | does not run, agent enters [Safe State](safe-state.md) |

The kill-switch is the exception: it is enforced in both modes.

If the gate itself fails (a bug, not a rule), the verdict is `BLOCK`: in `enforce` mode the action does not run, in `shadow` mode it runs and the error is recorded. The same goes for an axiom that raises. This is the fail-safe rule, and tests cover it (see [Claims](../claims.md), `fail-closed`).

`enforce(executor)` wraps a callable so that every call passes through `decide` first. A denied call raises `ActionBlocked` (`ActionLimited` for an unapproved `LIMIT`, `SafeStateActive` when the agent was already held) and the executor is not called.

## The observation path

After the executor returns or raises, `Gate.observe` records the result: latency, ok or error, tokens and cost. That feeds the [behavioural baseline and budget](budget.md) and queues an audit event.

The audit log never writes on the caller's thread. `emit` stamps the event and puts it on a bounded queue; one writer thread seals records into the [hash chain](audit-chain.md) and appends them. If the queue is full, the event is dropped and counted, and the chain records an `audit.gap` event later. The decision path never waits.

## What it costs

On the committed benchmark run (Apple M1, Python 3.10.21, 2026-11-27, audit off) one `decide` took a p50 of 11.9 to 14.1 µs with 1 to 10 axioms and a p99 of 15.0 to 15.4 µs with 10 axioms. With 100 axioms the p99 was 38.2 µs. The worst single call in any row was 195 µs. With the JSONL audit log on, p99 rose to 438 µs and the worst call to 3.4 ms (12.4 µs and 65 µs with audit off in that run). These numbers describe that machine only. Full tables, with p99 and max, are on the [Benchmarks](../evidence/benchmarks.md) page.

## The limit of the gate

The gate only covers actions that pass through the wrapped executor. An agent that reaches a tool by another route is not gated. See [Known limits](../known-limits.md).
