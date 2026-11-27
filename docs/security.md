# Security

This page is the threat model of Æon itself: what it protects, from whom, and what you must do if you run the runtime beyond your own laptop. To report a vulnerability, see [`SECURITY.md`](https://github.com/richardsonlima/aeon-core/blob/main/SECURITY.md): private advisories only, no public issues.

## Assets

| Asset | Why it matters |
|---|---|
| The gate's decisions and mode | If an attacker can change them, the gate stops protecting. |
| Axiom files and `aeon.toml` | Axiom files are **Python code that Æon imports and runs**. Whoever can write them can run code as your agent's user. |
| The audit log | The record of what the agent did and what the gate decided. |
| The runtime token | An **operator** credential for the HTTP API, which can switch the mode, engage the kill-switch, change policies, reset Safe State and run campaigns. |
| What the agent can do | The real target: the tools behind the gate. |

## Trust boundaries

- **Agent and gate share a process** when you use the library. Æon is not a sandbox: code running in the same process can bypass or patch the gate. It is a guard rail for an agent's tool calls, not isolation from hostile code.
- **Client and runtime** talk over HTTP on loopback by default, with a bearer token.
- **Runtime and filesystem**: the audit log, the token file and the campaign results are plain files with your user's permissions.
- **Model output and tool output are untrusted input** to the agent. That is the case the fault catalog simulates (poisoned output, conflicting instructions).

## Attacker capabilities considered

| Attacker | What Æon does | What it does not do |
|---|---|---|
| Injects instructions through tool output | The axioms judge the resulting **action**, not the text. A denied tool call is blocked in enforce mode. | It does not read or sanitise the text, and does not stop an action that no axiom objects to. |
| Other process or user on the same machine | The token file is created with mode `0600`; the API needs the token. | It does not defend against root, or against a user who can read your files. |
| Web page in your browser (DNS rebinding) | On a loopback bind the runtime accepts only the Host values `localhost`, `127.0.0.1` and `[::1]` and rejects others with "Invalid host header". `AEON_RUNTIME_ALLOWED_HOSTS` (comma-separated) sets the allowlist explicitly and also works on non-loopback binds and in containers. | On a non-loopback bind **without** that variable there is no Host check. Set it, or let your proxy enforce it. |
| Network attacker | The default bind is loopback and the runtime refuses to bind elsewhere unless `AEON_RUNTIME_ALLOW_REMOTE=1`. | There is **no TLS**. Without a proxy, the token and the data travel in clear text. |
| Large or malformed requests | Bodies above 1 MiB get a 413. Campaign API caps: `runs` and `controls` at most 1,000 each, `steps` at most 1,000, `(runs + controls) * steps` at most 50,000, and injected `*_ms` parameters between 0 and 5,000. Campaign targets are names, never file paths. At most 16 decision-stream (SSE) clients. Buffered decisions keep serialized arguments only up to 16 KiB. MCP stdio rejects any line above 4 MiB and survives deeply nested JSON. | There is no rate limiting of requests. |
| Someone who can write the audit file | Edits, removals in the middle and reordering are detected by `aeon audit verify`. Removal from the end is detected with `--expect-head`. | They can rebuild the whole chain. There is no signing or anchor yet. |

## What the token protects

Every `/v1` route needs `Authorization: Bearer <token>` and is compared in constant time. `/health` and `/version` are open and return nothing sensitive. The token comes from `AEON_RUNTIME_TOKEN` or from `.aeon/runtime.token`, created on first start with 32 random bytes and mode `0600` (an existing file is tightened to `0600`, and a symlink is refused). Every response carries `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` and a Content-Security-Policy with `frame-ancestors 'none'`. The server prints where the token is, never the token. The decision stream (`/v1/decisions/stream`) also accepts `?token=` because the browser `EventSource` cannot set headers, so avoid putting that URL in logs. The control plane UI keeps the token in the URL fragment, which is not sent to the server.

The token is an **operator credential** ([ADR 003](decisions/003-operator-token-and-axiom-trust.md)). It authorises everything the API does: **there are no roles**. Anyone with it can set the mode to shadow, change policies, release a Safe State or release the kill-switch. **Never give it to an agent.** An agent that holds the token can switch its own gate to shadow. An agent process that needs decisions should use the library (`enforce`) in its own process. A separate decision-only token is on the roadmap, not built.

## Axiom files are trusted code

Axiom files named in `aeon.toml` are imported as Python. Starting `aeon runtime start` or `aeon runtime mcp` inside a checkout you do not trust runs that checkout's code, like running its Makefile. Both commands print the resolved path of every axiom file at startup so you can see what is loaded. Config discovery walks up from the working directory, and there is no trust prompt for it yet (roadmap, not built). Run Æon only in directories you trust, or pass `--config` explicitly.

## Remote hardening checklist

Do not expose the runtime to a network until every box is ticked.

- [ ] A reverse proxy terminates **TLS** in front of it (the runtime has none).
- [ ] `AEON_RUNTIME_ALLOWED_HOSTS` lists the host names clients use (`compose.yaml` sets it to `localhost,127.0.0.1`), and the proxy limits who can connect; add rate limiting there.
- [ ] `AEON_RUNTIME_ALLOW_REMOTE=1` is set deliberately, and `AEON_RUNTIME_TOKEN` is a long random value from a secret store, not a file in the repository.
- [ ] You have a plan to **rotate the token**: change `AEON_RUNTIME_TOKEN` (or delete `.aeon/runtime.token`) and restart. There is no revocation list.
- [ ] The container runs read-only with a writable `/data` volume only, as a non-root user, with capabilities dropped (`compose.yaml` does this) and the port published on loopback or an internal network.
- [ ] The audit file has restrictive permissions (Æon creates it `0600`; keep it owned by the runtime's user), lives on storage the agent cannot write, and its head hash is copied elsewhere on a schedule.
- [ ] Only one process writes each audit file.
- [ ] `include_args` is `false` unless you accept raw arguments, which may hold secrets, in the log.
- [ ] Axiom files and `aeon.toml` are writable only by deployers, because they are code.
- [ ] The token is held by operators only, never by an agent process.

## Privacy and telemetry

Æon sends **no telemetry**. Nothing leaves the machine unless your own code sends it. `AEON_TELEMETRY` is ignored. By default the audit log stores the tool name, the argument names and a sha256 of the arguments (low-entropy arguments can be guessed from the hash). The documentation website uses system fonts and loads nothing from third parties; the Python package never contacts any server.

## MCP

`aeon runtime mcp` and `aeon docs mcp` use stdio and run with the privileges of the process that starts them. `aeon_run_campaign` writes results under `.aeon/campaigns/`. The docs server only reads `.md` files inside its docs directory and rejects `..`, absolute paths and escaping symlinks.

## Not covered

No formal verification, no penetration test, no third-party audit. The container image is built locally from the repository, and no image is published. The release pipeline plans an SBOM and build provenance, but nothing has been released yet. See [Known limits](known-limits.md).
