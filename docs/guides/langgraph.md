# Wrap a LangGraph agent

`guard_tools` wraps tool objects (anything with `name` and `invoke` or `ainvoke`) so every call passes the gate. Nothing from `langchain` is imported by Æon.

```python
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, create_react_agent

from aeon.adapters import guard_tools


@tool
def read_file(path: str) -> str:
    """Read a text file."""
    ...


@tool
def delete_file(path: str) -> str:
    """Delete a file."""
    ...


tools = guard_tools([read_file, delete_file], gate=gate, agent="my-agent")
agent = create_react_agent(model, tools)
# or: ToolNode(tools, handle_tool_errors=True)
```

- A denied call raises `ActionBlocked` and the tool body never runs.
- Pydantic tools (LangChain `BaseTool`) come back as copies with guarded `invoke` and `ainvoke`, so they are still `BaseTool` instances and `ToolNode` keeps working.
- With `handle_tool_errors=True`, the node turns `ActionBlocked` into a tool message the model can read. Without it the exception propagates out of the graph.
- Plain callables are wrapped with `enforce` and keep their own name.

Runnable with a scripted fake model: `python examples/langgraph_agent/main.py`.

The test suite exercises this adapter with test doubles that have the same `name` and `invoke` shape, and with `langchain_core` tools when that package is installed. I have not run it inside a full LangGraph graph.
