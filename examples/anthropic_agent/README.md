# Anthropic agent

A Messages API tool-use loop. The scripted fake model reads a file, then (as if prompt
injected by the file's content) asks to delete `prod.db`. The gate blocks the call and the
`tool_result` block comes back with `is_error: true` and `Æon blocked this action: ...`,
so the model can recover. Decisions are in `.aeon/audit.jsonl` (override with `AEON_AUDIT`).

```bash
python examples/anthropic_agent/main.py
aeon audit verify --file .aeon/audit.jsonl
```

## Use the real client

Replace the fake client (the line marked "Real client") with:

```python
import anthropic

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
```

and set `model=` to the model you use. `tool_specs(box)` returns `input_schema` tool
definitions, `run_tool_uses(resp, box)` returns the `tool_result` blocks for the next user
message, and `record_usage` adds input and output tokens to the gate's budget monitor.
