# MCP tools

Æon speaks MCP (newline-delimited JSON-RPC 2.0 over stdio, protocol version `2025-06-18`, and it accepts `2025-03-26` and `2024-11-05`). Logs go to stderr, never stdout, because stdout carries the protocol. Two servers:

## The gate: `aeon runtime mcp`

Builds a gate from your config and exposes four tools. Add it to an MCP client:

```json
{ "mcpServers": { "aeon": { "command": "aeon", "args": ["runtime", "mcp"] } } }
```

| Tool | Arguments | What it does |
|---|---|---|
| `aeon_check_action` | `tool` (required), `args` (object), `agent`, `approved` | Asks the gate whether the action may run. Returns the decision record. **The action is not executed.** |
| `aeon_status` | none | Mode, kill-switch, Safe States, counters, budget per agent, and audit health. |
| `aeon_audit_verify` | `expect_head` (optional hash) | Verifies the hash chain of the audit log. |
| `aeon_run_campaign` | `target` (required fault name or campaign file name), `runs`, `controls`, `seed`, `blast_radius` | Runs a chaos campaign against the simulated agent and returns the summary, checks and unfavourable results. Capped at 1000 runs and 1000 steps; the blast radius ceiling in your config applies; file paths are not accepted. |

Expected failures come back as tool results with `isError: true`, not as protocol errors.

An MCP client is not the same as a gated agent. `aeon_check_action` only helps if the agent is built to ask before it acts. The gate does not intercept tools of an agent that does not call it.

## The docs: `aeon docs mcp`

Serves the documentation. Tools: `search_docs` (`query`, optional `limit` 1 to 20; returns path, title and a snippet) and `read_doc` (`path`, a relative `.md` path or an `aeon-docs://` URI). Resources: every `.md` under the docs directory as `aeon-docs://<relative path>`. Paths with `..`, absolute paths and symlinks that leave the docs directory are rejected. `--docs-dir` points at another directory.

## Try it by hand

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"t","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"aeon_check_action","arguments":{"tool":"delete_file"}}}' \
  | aeon runtime mcp
```
