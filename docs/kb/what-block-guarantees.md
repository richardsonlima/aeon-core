# What BLOCK guarantees

Precisely, and no more. Each line is backed by a test listed on [Claims](../claims.md).

In **enforce** mode, for an action that goes through an enforced executor (`enforce(...)`, a `ToolBox`, `guard_tools`, or the runtime's evaluate call honoured by its client):

1. **The decision comes first.** The gate decides before the executor runs. A `BLOCK` verdict means the executor is not called and `ActionBlocked` is raised (`gate-before-execution`).
2. **The agent is held.** After a `BLOCK`, every later action of that agent is blocked with `SafeStateActive` until `gate.reset(agent)` (`safe-state`).
3. **Failure is closed.** If an axiom raises, or the gate itself fails, the action is blocked (`fail-closed`).
4. **An unapproved `LIMIT` does not run.** It raises `ActionLimited`, unless the action is approved or the approver hook says yes. A hook that raises does not approve.
5. **The kill-switch stops everything.** Every action of every agent, in any mode (`kill-switch`).
6. **The decision is recorded** on a best-effort basis: the event goes to a bounded queue and is written by a background thread (see below), and the chain lets you detect later tampering.

In **shadow** mode, none of 1 to 4 applies: the verdict is recorded and the action runs. Only the kill-switch is enforced.

## On the committed campaigns

In enforce mode, across the seven enforce campaigns (30 fault runs each), the number of unapproved destructive actions executed was 0. That is a measurement on a simulated agent that follows injected instructions with probability 0.7, and its only destructive tools are `delete_files` and `send_email`. It is not a proof.

## What it still does not give you

See [What it does not guarantee](what-it-does-not-guarantee.md). The short list: bypass paths, free text, dropped audit events, a rebuilt chain, and anything that happened before the gate was in front of the tool.
