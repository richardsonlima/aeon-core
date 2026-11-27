# Where it runs

Æon is a Python library and a command-line tool. It runs where your agent's tool calls run, because the gate is a function call in front of the tool.

| Where | How | Notes |
|---|---|---|
| **Local**, any Python agent | `pip install aeon-core`, wrap the executor with `enforce` | No server, no network, no account. Audit goes to a local file. |
| **Local, other languages or processes** | `aeon runtime start` and call `POST /v1/actions/evaluate` | Needs the `runtime` extra. Loopback by default. See [Runtime](../guides/runtime.md). |
| **Coding agents (MCP)** | `aeon runtime mcp` for the gate, `aeon docs mcp` for the docs | stdio transport. |
| **Docker** | `docker compose up --build` from the repository | Built locally; no image is published. See [Runtime](../guides/runtime.md). |
| **CI** | `aeon chaos run <campaign> --strict` | Fails the build when a hypothesis is not supported. See [CI gate](../guides/ci-gate.md). |
| **LangGraph, OpenAI, Anthropic** | `aeon.adapters` | Duck-typed; the SDK is yours. See the guides. |

## What it needs

- Python 3.10 or newer.
- A writable place for the audit log (default `.aeon/audit.jsonl`), or `audit = "off"`.
- Nothing else for the core. No dependencies, no telemetry, no account. See [Security](../security.md).

## What it does not do

- It does not call a model. The campaigns use a scripted simulated agent.
- It does not execute your tools for you through the runtime. The runtime only decides.
- One audit writer per log file, one gate per process. Running many processes against one audit file will fork the chain. See [Known limits](../known-limits.md).
