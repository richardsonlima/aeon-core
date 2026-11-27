# Wrap an Anthropic agent

`aeon.adapters.anthropic` is duck-typed too: it never imports the `anthropic` package. Tool use runs through a `ToolBox`.

```python
from aeon.adapters import ToolBox
from aeon.adapters.anthropic import record_usage, run_tool_uses, tool_specs
from aeon.axioms import Gate
from aeon.axioms.builtin import deny_tools
from aeon.baseline import Monitor

gate = Gate([deny_tools(["delete_file"])], mode="enforce", monitor=Monitor())
box = ToolBox(gate=gate, agent="anthropic-demo")


@box.tool
def read_file(path: str) -> str:
    """Read a text file."""
    return f"contents of {path}"


@box.tool
def delete_file(path: str) -> str:
    """Delete a file."""
    return f"deleted {path}"


# client = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY
messages = [{"role": "user", "content": "Summarise notes.txt"}]
while True:
    resp = client.messages.create(
        model="<the model you use>", max_tokens=1024, messages=messages, tools=tool_specs(box)
    )
    record_usage(resp, gate, agent="anthropic-demo")
    if resp.stop_reason != "tool_use":
        break
    messages.append({"role": "assistant", "content": resp.content})
    messages.append({"role": "user", "content": run_tool_uses(resp, box)})
```

- `tool_specs(box)` returns `input_schema` definitions built from type hints.
- `run_tool_uses(resp, box)` runs each `tool_use` block through the gate and returns `tool_result` blocks for the next user message. A denied call or a tool error comes back with `is_error: true` and the text `Æon blocked this action: ...`, so the model can recover.
- `record_usage` adds input and output tokens to the budget monitor.

Runnable with a scripted fake client: `python examples/anthropic_agent/main.py`.
