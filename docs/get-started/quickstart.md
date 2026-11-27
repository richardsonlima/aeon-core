# Quickstart (5 minutes)

You will gate a tiny agent, watch the gate record what it would block (shadow), turn blocking on (enforce), verify the audit log, and run a chaos campaign. Install first: [Install](install.md).

## 1. Scaffold and check

```bash
mkdir my-agent && cd my-agent
aeon init
aeon doctor
```

`aeon init` writes `aeon.toml` (in `shadow` mode) and `aeon_axioms.py` with example axioms. `aeon doctor` should end with `All checks passed.` and the line `gate self-test: block, Safe State, shadow, fail-closed, kill-switch and audit chain all behave`.

```bash
aeon axioms list
```

```text
BLOCK  no_destructive_tool_call  Destructive tools need explicit approval.
ALERT  flag_external_urls        Record calls that reach outside the company domain.
LIMIT  require_approval          require approval  [tools: deploy]
```

## 2. Gate an agent

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

The axioms come from `aeon_axioms.py`, which `aeon.toml` loads. Run it in shadow mode, then enforce:

```bash
aeon run agent.py
```

```text
read_file -> contents of notes.txt
delete_file -> deleted prod.db
[aeon] mode=shadow decisions=2 allowed=2 denied=0 gate_errors=0
```

```bash
aeon run agent.py --mode enforce
```

```text
read_file -> contents of notes.txt
delete_file -> blocked: Æon blocked 'delete_file' (BLOCK): Destructive tools need explicit approval.
[aeon] mode=enforce decisions=2 allowed=1 denied=1 gate_errors=0
```

In shadow mode `delete_file` ran, and the log says it would have been blocked.

## 3. Read and verify the audit log

```bash
aeon audit tail
aeon audit verify
```

```text
     2 2026-11-27T13:41:14.914Z BLOCK default/delete_file allowed (shadow) - Destructive tools need explicit approval.
     6 2026-11-27T13:41:14.962Z BLOCK default/delete_file DENIED (enforce) - Destructive tools need explicit approval.
     7 2026-11-27T13:41:14.962Z safe_state {"entered": true, "agent": "default", ...}
ok: 8 records, chain intact
head 815b18c7...
```

Change one record and verify again:

```bash
cp .aeon/audit.jsonl copy.jsonl && sed -i.bak 's/delete_file/read_file/' copy.jsonl
aeon audit verify --file copy.jsonl
```

```text
BROKEN at line 3, seq 2: hash mismatch: record content was changed
2 records verified before the break
```

The exit code is 1. Truncation from the end is only caught with `--expect-head`; see [Audit chain](../concepts/audit-chain.md).

## 4. Inject a fault

```bash
aeon chaos list
aeon chaos run "poisoned output" --runs 10 --controls 10
```

```text
[staging] fault poisoned-output injected from step 40 in 10 runs (10 controls)
  escalation (first run): BLOCK · Safe State reached
  detection 100%  false positives 20%  Safe State 100%  harmful actions executed 0
  hypothesis supported
```

Read the numbers twice: detection is 100%, and the false-positive rate is 20%. The gate raised the alarm on clean traffic of the simulated agent in 2 of 10 control runs. That is the kind of result Æon reports on purpose; see [Read a report](../guides/reports.md).

## Next

- Gate your own agent: [plain Python](../guides/plain-python.md), [OpenAI](../guides/openai.md), [Anthropic](../guides/anthropic.md), [LangGraph](../guides/langgraph.md).
- Keep it in shadow for a while: [Shadow-first adoption](../concepts/shadow-first.md).
- What this does not cover: [Known limits](../known-limits.md).
