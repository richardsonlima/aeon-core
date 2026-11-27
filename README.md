# Æon Core

[English](README.md) | [Português](README.pt.md)

![version](https://img.shields.io/badge/version-0.5.0.dev0-blue) ![license](https://img.shields.io/badge/license-Apache--2.0-green) ![python](https://img.shields.io/badge/python-3.10%2B-blue)

Æon is a free, open-source Python runtime that **gates the actions of LLM agents** and **injects controlled faults** to check that they fail safe.

You wrap the function through which your agent runs tools. Before each call, a small synchronous gate decides: go, alert, limit or block. After the call, an asynchronous path writes a hash-chained audit log and compares the agent with its own baseline. Chaos campaigns then break things on purpose (a timeout, a poisoned tool output, a 429) and report whether the gate caught it, false positives and misses included.

Inspired by the MECADE framework (chaos engineering for dependability); an independent project with no relation to any academic program.

## Status

**Alpha. Nothing is published to PyPI yet, and there is no 0.5.0 tag.** This is a ground-up rewrite of v0.4 (see [`CHANGELOG.md`](CHANGELOG.md) and the [audit](https://www.richardsonlima.com.br/aeon/docs/audit/)).

| Implemented and tested | Not built |
|---|---|
| Gate, axioms, autonomy levels, Safe State, kill-switch, shadow mode | Signed audit records and an external anchor for the chain |
| Hash-chained audit log (JSONL, SQLite) and `aeon audit verify` | A Postgres audit backend |
| Behavioural baseline, deviation score, CUSUM and envelope | Any test against a real LLM, and any field data |
| Eight faults with a blast-radius guard, pre-registered campaigns | Multi-process audit writers |
| Adapters for plain Python, OpenAI, Anthropic and LangGraph (duck-typed) | Certification of any kind (IEC 61508, DO-178C and similar are inspiration and roadmap only) |
| Local HTTP runtime, control plane UI, MCP servers for the gate and the docs | A published container image |

**Read [Known limits](https://www.richardsonlima.com.br/aeon/docs/known-limits/) before you rely on it.** The short version: the gate only covers actions that pass through the wrapped executor, axioms do not judge the meaning of free text, and on the committed campaigns the default budget raised false positives in up to 70% of clean control runs of a simulated agent (eight of nine pre-registered hypotheses were not supported).

## Install

Requires Python 3.10 or newer. The core has no third-party dependencies.

Not on PyPI yet, so install from a checkout of this repository:

```bash
cd aeon-core
pip install .                # or: pip install ".[runtime]" for the HTTP runtime
uv pip install .             # with uv
pipx install .               # as a command-line tool
```

Once the branch is on GitHub: `pip install "aeon-core @ git+https://github.com/richardsonlima/aeon-core@<branch>"`.

After the first release:

```bash
pip install aeon-core
uv add aeon-core
uvx --from aeon-core aeon version
pipx install aeon-core
```

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

## Documentation

- Docs: <https://www.richardsonlima.com.br/aeon/docs/> (English and Portuguese; also `docs/` in this repository, `aeon docs mcp` to serve it to a coding agent, and [`llms.txt`](llms.txt))
- [5-minute quickstart](https://www.richardsonlima.com.br/aeon/docs/get-started/quickstart/) and a [prompt for a coding agent](https://www.richardsonlima.com.br/aeon/docs/get-started/coding-agent/)
- [Claims](https://www.richardsonlima.com.br/aeon/docs/claims/): every claim with its evidence status
- [Known limits](https://www.richardsonlima.com.br/aeon/docs/known-limits/)
- [Benchmarks](benchmarks/README.md): how to reproduce, what they do not mean, and the unfavourable results. Every number describes one machine only.
- [Security](https://www.richardsonlima.com.br/aeon/docs/security/) and [`SECURITY.md`](SECURITY.md)
- [Contributing](CONTRIBUTING.md), [Release guide](RELEASE.md), [Changelog](CHANGELOG.md)

## License

Apache-2.0. See [`LICENSE`](LICENSE).
