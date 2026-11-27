# Safe State

Safe State is where an agent is held after an enforced `BLOCK`. It is per agent (the `agent` field of the action, `default` if you set none).

## What happens

- The first enforced `BLOCK` for an agent records a `SafeState` (reason, decision id, time) and emits a `safe_state` audit event.
- While the agent is held, **every** action of that agent gets a `safe-state` `BLOCK` finding in `enforce` mode, and raises `SafeStateActive`. The axioms still run, so the audit shows why each action would also have been objected to.
- Other agents are not affected.
- A `LIMIT` never enters Safe State.
- In `shadow` mode no agent enters Safe State, because nothing is enforced.

## Leaving it

Safe State does not expire. Someone releases it:

```python
gate.reset("my-agent")  # returns True if the agent was held
```

or `POST /v1/safe-state/{agent}/reset` on the [runtime](../guides/runtime.md). Releasing also clears the agent's accumulated deviation, its rolling window and its cost and token totals (the calibrated baseline stays). A `safe_state` audit event with `entered: false` is recorded.

## Kill-switch

The kill-switch is the operator's stop for everyone: `gate.engage_kill_switch("reason")` blocks every action of every agent, in `shadow` and `enforce` mode, until `gate.release_kill_switch()`. Because it is enforced, blocked agents enter Safe State too. Both calls are audited.

## What Safe State is not

It does not undo anything the agent already did, and it does not stop an agent from acting through a path that bypasses the gate. See [What BLOCK guarantees](../kb/what-block-guarantees.md).
