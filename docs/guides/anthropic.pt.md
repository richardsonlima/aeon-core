# Proteger um agente Anthropic

`aeon.adapters.anthropic` também usa duck typing: nunca importa o pacote `anthropic`. O uso de ferramentas passa por um `ToolBox`.

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
    """Lê um arquivo de texto."""
    return f"contents of {path}"


@box.tool
def delete_file(path: str) -> str:
    """Apaga um arquivo."""
    return f"deleted {path}"

# client = anthropic.Anthropic()   # lê ANTHROPIC_API_KEY
messages = [{"role": "user", "content": "Resuma notes.txt"}]
while True:
    resp = client.messages.create(
        model="<o modelo que você usa>", max_tokens=1024, messages=messages, tools=tool_specs(box)
    )
    record_usage(resp, gate, agent="anthropic-demo")
    if resp.stop_reason != "tool_use":
        break
    messages.append({"role": "assistant", "content": resp.content})
    messages.append({"role": "user", "content": run_tool_uses(resp, box)})
```

- `tool_specs(box)` devolve definições com `input_schema` montadas a partir dos type hints.
- `run_tool_uses(resp, box)` roda cada bloco `tool_use` pelo gate e devolve blocos `tool_result` para a próxima mensagem do usuário. Uma chamada negada ou um erro de ferramenta volta com `is_error: true` e o texto `Æon blocked this action: ...`, para o modelo se recuperar.
- `record_usage` soma tokens de entrada e saída ao monitor de orçamento.

Executável com um cliente falso roteirizado: `python examples/anthropic_agent/main.py`.
