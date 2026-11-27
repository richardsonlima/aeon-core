# Proteger um agente LangGraph

`guard_tools` envolve objetos de ferramenta (qualquer coisa com `name` e `invoke` ou `ainvoke`) para que toda chamada passe pelo gate. O Æon não importa nada de `langchain`.

```python
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, create_react_agent

from aeon.adapters import guard_tools


@tool
def read_file(path: str) -> str:
    """Lê um arquivo de texto."""
    ...


@tool
def delete_file(path: str) -> str:
    """Apaga um arquivo."""
    ...


tools = guard_tools([read_file, delete_file], gate=gate, agent="my-agent")
agent = create_react_agent(model, tools)
# ou: ToolNode(tools, handle_tool_errors=True)
```

- Uma chamada negada levanta `ActionBlocked` e o corpo da ferramenta nunca roda.
- Ferramentas Pydantic (`BaseTool` do LangChain) voltam como cópias com `invoke` e `ainvoke` protegidos, então continuam sendo instâncias de `BaseTool` e o `ToolNode` segue funcionando.
- Com `handle_tool_errors=True`, o nó transforma `ActionBlocked` numa mensagem de ferramenta que o modelo lê. Sem isso a exceção sobe para fora do grafo.
- Callables comuns são envolvidos com `enforce` e mantêm o próprio nome.

Executável com um modelo falso roteirizado: `python examples/langgraph_agent/main.py`.

A suíte de testes exercita este adaptador com dublês de teste que têm o mesmo formato de `name` e `invoke`, e com ferramentas de `langchain_core` quando esse pacote está instalado. Não o executei dentro de um grafo LangGraph completo.
