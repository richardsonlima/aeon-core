# Wrap an OpenAI agent

`aeon.adapters.openai` is duck-typed: it does not import the `openai` package, so it works with the real client, dicts and test doubles. The tool loop does not change, except that tool calls run through a `ToolBox`.

```python
import json
import os
from types import SimpleNamespace as NS

from aeon.adapters import ToolBox
from aeon.adapters.openai import record_usage, run_tool_calls, tool_specs
from aeon.audit import AuditLog
from aeon.axioms import Gate
from aeon.axioms.builtin import deny_tools
from aeon.baseline import Monitor

audit = AuditLog(os.environ.get("AEON_AUDIT", ".aeon/audit.jsonl"))
gate = Gate([deny_tools(["delete_file"])], mode="enforce", audit=audit, monitor=Monitor())
box = ToolBox(gate=gate, agent="openai-demo")


@box.tool
def read_file(path: str) -> str:
    """Read a text file."""
    return f"contents of {path}"


@box.tool
def delete_file(path: str) -> str:
    """Delete a file."""
    return f"deleted {path}"


# client = OpenAI()   # reads OPENAI_API_KEY
messages = [{"role": "user", "content": "Summarise notes.txt"}]
specs = tool_specs(box)
while True:
    resp = client.chat.completions.create(model="gpt-4o", messages=messages, tools=specs)
    record_usage(resp, gate, agent="openai-demo")
    msg = resp.choices[0].message
    if not msg.tool_calls:
        break
    messages.append(msg)
    messages.extend(run_tool_calls(msg, box))
```

- `tool_specs(box)` builds Chat Completions tool definitions from your type hints and docstrings. Pass `api="responses"` for the Responses API.
- `run_tool_calls(msg, box)` runs every call through the gate and returns `role: tool` messages (or `function_call_output` items for the Responses API). A denied call comes back as the text `Æon blocked this action: ...`, so the model can recover. Nothing in it raises for a blocked action, an unknown tool or malformed arguments.
- `record_usage` adds the response's token total to the budget monitor.

The repository has a runnable version with a scripted fake client, no network needed: `python examples/openai_agent/main.py`.

!!! warning "What is gated"
    The gate sees the tool call, not the model's text. A model that answers with harmful free text without calling a tool is not stopped. See [Known limits](../known-limits.md).
