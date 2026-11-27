# LangGraph agent

`guard_tools` wraps tool objects (anything with `name` and `invoke` / `ainvoke`) so every
call passes the gate. A denied call raises `ActionBlocked` and the tool body never runs.
The scripted fake model reads a file, then asks to delete `prod.db`; the gate blocks it.
Decisions are in `.aeon/audit.jsonl` (override with `AEON_AUDIT`).

```bash
python examples/langgraph_agent/main.py
```

## Use real LangGraph tools

```python
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, create_react_agent
from aeon.adapters import guard_tools


@tool
def read_file(path: str) -> str: ...


tools = guard_tools([read_file, delete_file], gate=gate, agent="my-agent")
agent = create_react_agent(model, tools)
# or: ToolNode(tools, handle_tool_errors=True)
```

Pydantic tools (`BaseTool`) come back as copies with guarded `invoke` / `ainvoke`, so
they are still `BaseTool` instances. With `handle_tool_errors=True` the node turns
`ActionBlocked` into a tool message the model can read; without it the exception
propagates out of the graph.
