# Site changes (for review)

Changes the public site at `richardsonlima.com.br/aeon` needs so that it matches what the code does. I have not edited the site repository. Each item says what is wrong, why, and what to put instead.

| # | On the site | Problem | Replace with |
|---|---|---|---|
| 1 | Axiom example `@axiom(on_violation="BLOCK", response_time_ms=0.1)` | There is no `response_time_ms` argument on `axiom`, and no committed measurement supported 0.1 ms. The measured figure on one machine is p99 12.6 µs with 10 axioms, but the max of the same row was 125 µs, above 0.1 ms. | Drop the argument, or write the measured number with its context: "p99 12.6 µs, max 125 µs, 10 axioms, Apple M1, Python 3.12.14, 2026-11-27", linking to [Benchmarks](evidence/benchmarks.md). |
| 2 | Audit sample line ending `sig=ed25519:ok` | Signing is not implemented. The record has `seq`, `ts`, `type`, `data`, `prev` and `hash` (sha256). | Remove `sig=...`. Show a real `aeon audit tail` line, for example `6 2026-11-27T13:41:14.962Z BLOCK default/delete_file DENIED (enforce) - Destructive tools need explicit approval.`. If signing is mentioned, say "roadmap, not built". |
| 3 | Quickstart `from aeon import Agent, ChaosBudget` | `Agent` does not exist. `ChaosBudget` exists and is an alias of `Budget`. | Use the enforce-based quickstart: `from aeon.axioms import axiom, enforce`, wrap your executor with `enforce`, then `aeon run agent.py` (see the [quickstart](get-started/quickstart.md)). Keep `ChaosBudget(p99_ms=300, error_rate=0.02)` only where a budget is the topic, noting it equals `Budget(...)`. |
| 4 | `aeon serve` | Works, and is now a documented alias of `aeon runtime start`. | Keep it, and mention the canonical `aeon runtime start`. It needs `pip install "aeon-core[runtime]"`. |
| 5 | `aeon.yaml` | The config file is `aeon.toml` (or `[tool.aeon]` in `pyproject.toml`). | Replace `aeon.yaml` with `aeon.toml` and show a TOML snippet from [Configuration](reference/config.md). |
| 6 | "aeon-axioms, a standalone module" | There is no separate distribution. The axiom engine is the `aeon.axioms` subpackage of `aeon-core`, and it has no third-party dependencies. | Say "the dependency-free `aeon.axioms` subpackage of `aeon-core`", and do not tell people to `pip install aeon-axioms`. |
| 7 | No link to the docs | The docs now exist. | Add a visible link to `https://www.richardsonlima.com.br/aeon/docs/`, and to [Known limits](known-limits.md) and [Claims](claims.md). |
| 8 | Any SIL, DO-178C, IEC 61508 or "production-ready" wording | The code has no certification and no field data, and the v0.4 audit found the same wording in the old repository. | Use "inspired by" or "roadmap" only, and say alpha. See the [audit](audit.md). |
| 9 | Install instructions | Nothing is on PyPI yet. | Show `pip install aeon-core` only labelled "after the first release", and the checkout install from [Install](get-started/install.md) until then. |

I could not see the site's current source while writing this list. Items 1, 2 and 3 come from the [audit](audit.md), the others from comparing the site's public names with the code. Check each against the live page before editing.
