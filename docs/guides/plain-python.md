# Wrap a plain Python agent

Any agent that runs tools through one function can be gated by wrapping that function. This is the whole integration.

## 1. Wrap the executor

```python
from aeon.axioms import ActionBlocked, axiom, enforce

DESTRUCTIVE = {"delete_file", "drop_table", "send_email"}


@axiom(on_violation="BLOCK")
def no_destructive_tool_call(action):
    """A destructive tool runs only when a human approved it."""
    return action.tool not in DESTRUCTIVE or action.approved


@enforce
def run_tool(tool, args):
    tools = {
        "read_file": lambda path: f"contents of {path}",
        "delete_file": lambda path: f"deleted {path}",
    }
    return tools[tool](**args)


for tool, args in [("read_file", {"path": "notes.txt"}), ("delete_file", {"path": "prod.db"})]:
    try:
        print(tool, "->", run_tool(tool, args))
    except ActionBlocked as exc:
        print(tool, "-> blocked:", exc)
```

`enforce` picks how to read an action from the function signature, once, when you wrap it:

| Signature | The action is |
|---|---|
| first parameter named `action` | the `Action` you pass |
| first two parameters named like `(tool, args)` (also `tool_name`, `name`, and `arguments`, `input`, `tool_input`, `params`) | tool name and args from those parameters |
| anything else | the function itself is the tool, its bound arguments are the args |

Pass `tool="name"`, `agent="id"` or `to_action=` to override. `enforce` also works on `async def` and as a decorator.

## 2. Run it in shadow, then enforce

With no config the gate is in shadow mode and logs to `.aeon/audit.jsonl`. Run it under the CLI; without `--mode` it uses the mode in `aeon.toml` (shadow if there is none), and `--mode` overrides it:

```bash
aeon run agent.py                  # shadow: delete_file runs, the BLOCK verdict is recorded
aeon run agent.py --mode enforce   # enforce: delete_file is blocked
aeon audit tail
aeon audit verify
```

## 3. Use a `ToolBox` when you have many tools

`aeon.adapters.ToolBox` registers plain functions and routes every call through the gate:

```python
from aeon.adapters import ToolBox

box = ToolBox(gate=gate, agent="support-bot")


@box.tool
def read_file(path: str) -> str: ...


box.call("read_file", {"path": "notes.txt"})  # raises ActionBlocked if denied
box.safe_call("read_file", {"path": "notes.txt"})  # returns text for the model instead of raising
```

## 4. Name your agents

The `agent` field keys the [baseline](../concepts/budget.md) and [Safe State](../concepts/safe-state.md). Give each agent a stable name, or they will share one baseline.
