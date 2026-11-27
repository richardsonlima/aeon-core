# Æon Core

Æon is a free, open-source Python runtime that **gates the actions of LLM agents** and **injects controlled faults** to check that they fail safe.

You wrap the function through which your agent runs tools. Before each call, a small synchronous gate decides: go, alert, limit or block. After the call, an asynchronous path records a hash-chained audit log and compares the agent against its own baseline. Chaos campaigns then break things on purpose (a timeout, a poisoned tool output, a 429) and report whether the gate caught it, with the false positives and misses printed next to the wins.

*Inspired by the MECADE framework (chaos engineering for dependability); an independent project with no relation to any academic program.*

!!! warning "Status: alpha, v0.5.0 in development"
    Alpha, published to PyPI as `aeon-core`. The gate, audit chain, budget, fault catalog, campaigns, adapters, runtime and MCP servers are implemented and tested. Signed audit records, an external anchor for the chain, a Postgres backend and any test against a real LLM are **not built**. Read [Known limits](known-limits.md) before you rely on it.

## Start here

<div class="grid cards" markdown>

- **[Install](get-started/install.md)** and run the **[5-minute quickstart](get-started/quickstart.md)**
- **[Prompt for a coding agent](get-started/coding-agent.md)** that wires Æon in using documented commands only
- **[Gate and observation path](concepts/gate.md)**: what runs when, and why the split
- **[Shadow-first adoption](concepts/shadow-first.md)**: shadow, then `ALERT`, `LIMIT`, `BLOCK`

</div>

## What you get

| | |
|---|---|
| **Gate** | `@axiom` rules and `enforce(executor)`. Fail-safe: if a rule or the gate raises, the action is blocked in enforce mode. Kill-switch and per-agent [Safe State](concepts/safe-state.md). |
| **Shadow mode** | The default. Every verdict is recorded, none is enforced. |
| **Audit chain** | Append-only, hash-chained, written off the decision path. `aeon audit verify` finds the first broken link. |
| **Budget** | Per-agent baseline, deviation score, CUSUM, and an absolute envelope. [The math](concepts/budget.md). |
| **Chaos** | Eight faults with a blast-radius guard, pre-registered [campaigns](guides/campaigns.md), Wilson intervals, control runs. |
| **Adapters** | Plain Python, OpenAI, Anthropic, LangGraph. Duck-typed: no SDK is imported. |
| **Runtime** | Local FastAPI service, control plane UI, MCP servers for the gate and for these docs. |

## Evidence, with the bad news

Every number in these docs comes from committed results of one machine (Apple M1, Python 3.10.21, 2026-11-27), and each page says so. They describe that machine only.

- One gate decision: p99 15.0 µs with 10 axioms, but the worst single call in the run was 195 µs, and the audit queue dropped 2,081 of 50,000 events in a burst test.
- Of nine pre-registered campaigns (eight enforce, one shadow), **eight did not meet their hypothesis**: six on false positives (20% to 70% of clean control runs of the simulated agent raised the alarm) and two on the Safe State check. In the enforce campaigns where a destructive action was attempted, none ran.

See [Benchmarks](evidence/benchmarks.md), [Claims](claims.md) and the [first unfavourable result](blog/first-unfavourable-result.md).

## Honest scope

- The gate only covers actions that pass through the wrapped executor.
- Axioms do not judge the semantic correctness of free text.
- Chaos injection is not a substitute for a safety case. There is no certification of any kind; standards such as IEC 61508 or DO-178C are inspiration at most, and on the roadmap, not claimed.

License: Apache-2.0. Source: [github.com/richardsonlima/aeon-core](https://github.com/richardsonlima/aeon-core). I am Richardson Lima, and I write these docs in the first person where it matters.
