# OpenAI agent

A Chat Completions tool loop. The scripted fake model reads a file, then (as if prompt
injected by the file's content) asks to delete `prod.db`. The gate blocks that call, the
model receives `Æon blocked this action: ...` as the tool result and answers without it.
Every decision is in the audit log, `.aeon/audit.jsonl` (override with `AEON_AUDIT`).

```bash
python examples/openai_agent/main.py
aeon audit verify --file .aeon/audit.jsonl
```

## Use the real client

`main.py` builds the fake client in the lines marked "Real client". Replace them with:

```python
from openai import OpenAI

client = OpenAI()  # reads OPENAI_API_KEY
```

The loop is unchanged. `tool_specs(box)` returns Chat Completions tool definitions; pass
`api="responses"` for the Responses API, and feed `run_tool_calls(response, box)` the full
response: it returns `function_call_output` items instead of `role: tool` messages.
`record_usage` adds the response's tokens to the gate's budget monitor.
