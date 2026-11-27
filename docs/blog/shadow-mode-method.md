# Shadow mode, and what I can and cannot say about it

!!! note "Draft for review"
    Not published. Written by Richardson Lima.

I would like to write "here is what shadow mode found in production". I cannot. **There is no field data yet.** Nobody, me included, has run Æon in shadow on a production agent and reported what happened. What I have is a method, a mechanism, and a simulation. This post is about the method, and about being clear on which of those three each claim rests on.

## The method

1. **Wrap and record.** Wrap the executor with `enforce`, keep `mode = "shadow"`, keep audit on. Nothing is stopped. The only thing that changes is that every decision and its reasons are written to a hash-chained log.
2. **Read the log before you trust a rule.** `aeon audit tail --type decision`, or export to CSV. For every verdict at `BLOCK`, ask whether stopping would have been right.
3. **Count the wrong ones.** A rule's false-positive rate on your own traffic is the number that decides whether it can ever be `BLOCK`.
4. **Watch the budget separately.** The behavioural budget needs a baseline period and its defaults are not tuned for your agent. Look at each agent's `accumulated` and `max_accumulated` on clean traffic, and set thresholds above what clean traffic produces.
5. **Promote one rule at a time.** `ALERT`, then `LIMIT` (with an approval path), then `BLOCK` for rules you can explain.
6. **Rehearse the exit.** Know how to reset Safe State and how to engage the kill-switch before you need them.

## What it rests on

- **Mechanism (solid):** in shadow mode the gate records the verdict and lets the action run. Tests cover that shadow never enforces, except for the kill-switch.
- **Simulation (suggestive):** in my shadow campaign on the scripted agent, 385 unapproved destructive actions ran across 30 fault runs while the gate recorded a `BLOCK` for each, and 1 of 30 clean control runs raised a `BLOCK`. That tells me shadow measures exposure. It does not tell me what a real agent would do.
- **Field evidence (none):** I have no case where shadow mode caught a real incident, or a real team that moved a rule from shadow to enforce.

## What would count as evidence

If you try this, the useful report is small: how many decisions per day, how many verdicts per level, how many of the `BLOCK`s you judged wrong, whether `audit.gap` appeared, and how long calibration took. A number like that from a real agent, including a bad one, is worth more than anything I measured on a simulated one. I will publish what people send me, unfavourable results included.

See also: [Shadow-first adoption](../concepts/shadow-first.md), [Roll out in shadow mode](../guides/shadow-rollout.md).
