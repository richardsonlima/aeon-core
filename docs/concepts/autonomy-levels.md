# Autonomy levels

Four levels, ordered by severity. An axiom declares the level at which it objects (`on_violation`), and the gate's verdict is the highest level among all findings.

| Level | Meaning | In `shadow` | In `enforce` |
|---|---|---|---|
| `GO` | No rule objected. | runs | runs |
| `ALERT` | Record it, never interfere. | runs, recorded | runs, recorded |
| `LIMIT` | Restrict: the action needs approval. | runs, recorded | runs only if `approved`, or the approver hook returns true; otherwise `ActionLimited` |
| `BLOCK` | Stop the action and hold the agent. | runs, recorded | does not run, `ActionBlocked`, agent enters [Safe State](safe-state.md) |

`GO` is a verdict, not something you declare: `@axiom(on_violation="GO")` is rejected.

## Approval

An action is approved when `Action.approved` is true, which your code sets after a human says yes. A gate can also take an approver hook, `approver(decision) -> bool`, called only for an enforced `LIMIT`. A hook that raises does not approve. A `LIMIT` never moves the agent to Safe State.

## Where levels come from

- Axioms: `@axiom(on_violation="BLOCK")`, or the built-in factories in `aeon.axioms.builtin` (`deny_tools`, `allow_tools`, `rate_limit`, `deny_arg_pattern`, `require_approval`). See [Write an axiom](../guides/axioms.md).
- The budget: accumulated deviation crossing `alert_at`, `limit_at` or `block_at`, or an envelope breach at `on_breach`. See [Budget and deviation](budget.md).
- The kill-switch: always `BLOCK`.

## Moving up

Do not start at `BLOCK`. The path is shadow, then `ALERT`, then `LIMIT`, then `BLOCK` for the few rules you trust. See [Shadow-first adoption](shadow-first.md).
