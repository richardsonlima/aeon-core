# Æon Core

[English](https://github.com/richardsonlima/aeon-core/blob/main/README.md) | [Português](https://github.com/richardsonlima/aeon-core/blob/main/README.pt.md)

![version](https://img.shields.io/badge/version-0.5.0-blue) ![license](https://img.shields.io/badge/license-Apache--2.0-green) ![python](https://img.shields.io/badge/python-3.10%2B-blue)

Æon is a free, open-source Python runtime that **gates the actions of LLM agents** and **injects controlled faults** to check that they fail safe.

You wrap the function through which your agent runs tools. Before each call, a small synchronous gate decides: go, alert, limit or block. After the call, an asynchronous path writes a hash-chained audit log and compares the agent with its own baseline. Chaos campaigns then break things on purpose (a timeout, a poisoned tool output, a 429) and report whether the gate caught it, false positives and misses included.

Inspired by the MECADE framework (chaos engineering for dependability); an independent project with no relation to any academic program.

## Status

**Alpha.** Install with `pip install aeon-core`. This is a ground-up rewrite of v0.4 (see [`CHANGELOG.md`](https://github.com/richardsonlima/aeon-core/blob/main/CHANGELOG.md) and the [audit](https://www.richardsonlima.com.br/aeon/docs/audit/)).

| Implemented and tested | Not built |
|---|---|
| Gate, axioms, autonomy levels, Safe State, kill-switch, shadow mode | Signed audit records and an external anchor for the chain |
| Hash-chained audit log (JSONL, SQLite) and `aeon audit verify` | A Postgres audit backend |
| Behavioural baseline, deviation score, CUSUM and envelope | Field data, and a measured rate of anything on a real LLM |
| Eight faults with a blast-radius guard, pre-registered campaigns | Multi-process audit writers |
| Adapters for plain Python, OpenAI, Anthropic and LangGraph (duck-typed) | Certification of any kind (IEC 61508, DO-178C and similar are inspiration and roadmap only) |
| Local HTTP runtime, control plane UI, MCP servers for the gate and the docs | A published container image |
| Agent SDK: `Agent`, `Team`, `Workflow`, sessions, memory, approval, structured output; runs on real models (OpenRouter, OpenAI, Anthropic, Ollama) | Token streaming, async runs, RAG ([roadmap](https://www.richardsonlima.com.br/aeon/docs/roadmap/agent-sdk/)) |

**Read [Known limits](https://www.richardsonlima.com.br/aeon/docs/known-limits/) before you rely on it.** The short version: the gate only covers actions that pass through the wrapped executor, axioms do not judge the meaning of free text, and on the committed campaigns the default budget raised false positives in up to 70% of clean control runs of a simulated agent (eight of nine pre-registered hypotheses were not supported).

## Install

Requires Python 3.10 or newer. The core has no third-party dependencies.

```bash
pip install aeon-core            # or: pip install "aeon-core[runtime]" for the HTTP runtime
uv add aeon-core                 # in a project
uvx --from aeon-core aeon version
pipx install aeon-core           # as a command-line tool
```

0.3.0 and 0.4.0 on PyPI are the old code line; 0.5.0 is a rewrite with a different API.

## Quickstart

```bash
mkdir my-agent && cd my-agent
aeon init            # writes aeon.toml (shadow mode) and aeon_axioms.py
aeon doctor
```

Save as `agent.py`:

```python
from aeon.axioms import ActionBlocked, enforce


@enforce
def run_tool(tool, args):
    return {
        "read_file": lambda path: f"contents of {path}",
        "delete_file": lambda path: f"deleted {path}",
    }[tool](**args)


for tool, args in [("read_file", {"path": "notes.txt"}), ("delete_file", {"path": "prod.db"})]:
    try:
        print(tool, "->", run_tool(tool, args))
    except ActionBlocked as exc:
        print(tool, "-> blocked:", exc)
```

```bash
aeon run agent.py                  # shadow: delete_file runs, the BLOCK verdict is recorded
aeon run agent.py --mode enforce   # enforce: delete_file is blocked
aeon audit tail
aeon audit verify                  # ok: 8 records, chain intact
aeon chaos run "poisoned output" --runs 10 --controls 10
```

Start in shadow mode, read the log, and move one rule at a time to `ALERT`, `LIMIT`, then `BLOCK`.

## Develop

```bash
git clone https://github.com/richardsonlima/aeon-core && cd aeon-core
uv sync --group dev --extra runtime
uv run --no-sync pytest
```

[`CONTRIBUTING.md`](https://github.com/richardsonlima/aeon-core/blob/main/CONTRIBUTING.md) has every check CI runs (lint, types, tests, package smoke test, dependency audit, docs), the benchmarks, how to run the control plane on port 8787, and the rules for branches, commits and claims.

## Documentation

- Docs: <https://www.richardsonlima.com.br/aeon/docs/> (English and Portuguese; also `docs/` in this repository, `aeon docs mcp` to serve it to a coding agent, and [`llms.txt`](https://github.com/richardsonlima/aeon-core/blob/main/llms.txt))
- [5-minute quickstart](https://www.richardsonlima.com.br/aeon/docs/get-started/quickstart/) and a [prompt for a coding agent](https://www.richardsonlima.com.br/aeon/docs/get-started/coding-agent/)
- [Claims](https://www.richardsonlima.com.br/aeon/docs/claims/): every claim with its evidence status
- [Known limits](https://www.richardsonlima.com.br/aeon/docs/known-limits/)
- [Benchmarks](https://github.com/richardsonlima/aeon-core/blob/main/benchmarks/README.md): how to reproduce, what they do not mean, and the unfavourable results. Every number describes one machine only.
- [Security](https://www.richardsonlima.com.br/aeon/docs/security/) and [`SECURITY.md`](https://github.com/richardsonlima/aeon-core/blob/main/SECURITY.md)
- [Contributing](https://github.com/richardsonlima/aeon-core/blob/main/CONTRIBUTING.md), [Release guide](https://github.com/richardsonlima/aeon-core/blob/main/RELEASE.md), [Changelog](https://github.com/richardsonlima/aeon-core/blob/main/CHANGELOG.md)

## License

Apache-2.0. See [`LICENSE`](https://github.com/richardsonlima/aeon-core/blob/main/LICENSE).
