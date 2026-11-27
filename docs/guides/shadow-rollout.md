# Roll out in shadow mode

A concrete sequence for putting the gate in front of a real agent without stopping anything on day one. The reasoning is in [Shadow-first adoption](../concepts/shadow-first.md).

## Day 1: shadow, audit on

```bash
aeon init                    # writes aeon.toml (mode = "shadow") and aeon_axioms.py
aeon doctor
```

Wrap the executor with `enforce` (see [plain Python](plain-python.md) or an adapter) and ship. Nothing is stopped. Every decision goes to `.aeon/audit.jsonl`. If you cannot write to local disk, use `audit = "memory"` or an `sqlite:` path, and keep in mind that "off" means no record.

## First week: read the log

```bash
aeon audit tail -n 200 --type decision
aeon audit export --format csv -o decisions.csv
aeon audit verify
```

Questions to answer from real traffic:

1. Which axioms fire, how often, on which tools?
2. For the verdicts at `BLOCK`, would stopping have been right? Count the wrong ones.
3. What does the baseline look like? `GET /v1/status` (or `aeon_status` over MCP) shows each agent's calibration progress, `deviation`, `accumulated` and level.
4. Is `audit.gap` appearing? Then your event rate exceeds the queue.

## Then: promote one rule at a time

1. Set the budget's thresholds from what you saw ([How to calibrate a budget](../kb/calibrate-budget.md)). Keep it at `ALERT` first.
2. Switch the rules you trust to `LIMIT` and wire an approval path.
3. Switch to `enforce` for one agent, with one `BLOCK` rule you can explain. Keep the others in shadow. The mode is gate-wide, so use a separate gate or deployment if you need per-agent modes.
4. Rehearse the exit: `gate.reset("agent")` and the kill-switch, so the first Safe State is not the first time anyone used them.

## Rolling back

Set `mode = "shadow"` (or `AEON_MODE=shadow`, or `POST /v1/mode`). The change is recorded in the audit log as a `mode` event.

## Before you trust a verdict

Run a [campaign](campaigns.md) with a fault that matters to you, in `staging`. And read [What BLOCK guarantees](../kb/what-block-guarantees.md) and [Known limits](../known-limits.md).
