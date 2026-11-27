# Runtime, control plane and Docker

The runtime is a small FastAPI service around one gate, for agents that are not Python or that live in another process. It **never executes a tool**: a caller asks whether an action may run, and acts on the answer itself.

## Install and start

```bash
pip install "aeon-core[runtime]"
aeon runtime start                    # alias: aeon serve
```

```text
aeon runtime listening on http://127.0.0.1:8787
mode shadow; bearer token in /path/to/project/.aeon/runtime.token
```

Defaults: host `127.0.0.1`, port 8787. The token comes from `AEON_RUNTIME_TOKEN` if set, otherwise from `.aeon/runtime.token` (created with mode `0600` on first start). The runtime refuses to start on a non-loopback address unless `AEON_RUNTIME_ALLOW_REMOTE=1`. Read [Security](../security.md) before you change that. The token is an operator credential: never hand it to an agent. At startup the runtime also prints the path of every axiom file it loads, because those files are trusted Python.

## Ask for a decision

```bash
TOKEN=$(cat .aeon/runtime.token)
curl -s -X POST localhost:8787/v1/actions/evaluate \
  -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"tool":"delete_file","args":{"path":"prod.db"},"agent":"demo"}'
```

```json
{"agent":"demo","tool":"delete_file","verdict":"BLOCK","mode":"shadow","allowed":true,"enforced":false,"safe_state":false,"findings":[{"axiom":"no_destructive_tool_call","level":"BLOCK","reason":"Destructive tools need explicit approval."}], "...": "..."}
```

In shadow mode the verdict is `BLOCK` and `allowed` is still `true`. Your agent runs the tool, then reports how it went with `POST /v1/actions/result` so the baseline sees it. In enforce mode your client must honour `allowed: false`. The full list is in the [HTTP API reference](../reference/http-api.md).

## MCP

`aeon runtime mcp` serves the gate over MCP on stdio, with the tools `aeon_check_action`, `aeon_status`, `aeon_audit_verify` and `aeon_run_campaign` ([reference](../reference/mcp.md)). `aeon docs mcp` serves these docs to a coding agent.

## Control plane (UI)

```bash
aeon ui          # starts the runtime and opens the browser against it
aeon ui --no-browser
```

The UI is static files served by the runtime at `/ui/`, and it has views for overview, decisions, campaigns, the audit log and claims, all through the same API. The token travels in the URL fragment (`#token=...`), which browsers do not send to the server.

With `--no-browser`, open it yourself: `http://127.0.0.1:8787/ui/#token=<token>`, where the token is the content of the file the runtime prints at startup (`.aeon/runtime.token` by default). `--host` and `--port` change the address.

On a remote machine, keep the runtime on loopback and forward the port over SSH instead of binding to a public address:

```bash
ssh -L 8787:127.0.0.1:8787 user@server   # on your computer
aeon ui --no-browser                     # on the server
```

Then open `http://127.0.0.1:8787/ui/#token=<token>` in your local browser.

## Docker

The repository has a `Dockerfile` and `compose.yaml`. Nothing is published: no image is pushed anywhere. Build locally:

```bash
python -c "import secrets;print('AEON_RUNTIME_TOKEN=' + secrets.token_urlsafe(32))" > aeon.env
docker compose up --build
```

The container runs as a non-root user, binds `0.0.0.0` inside (so the image sets `AEON_RUNTIME_ALLOW_REMOTE=1`), and `compose.yaml` publishes the port on `127.0.0.1` only, with a read-only root filesystem, all capabilities dropped and `no-new-privileges`. Data lives in the `/data` volume. Do not commit `aeon.env`.

I have not run the container build in the environment where I wrote this page (no Docker there), so treat the compose file as reviewed, not exercised.

## Limits

The decisions page, stream and counters only see decisions made through this runtime process; decisions made elsewhere appear only in the audit log. One gate per process, one audit writer per log file, no Postgres backend. A campaign started over HTTP runs on one worker thread, one at a time. See [Known limits](../known-limits.md).
