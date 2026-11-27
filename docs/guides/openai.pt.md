# Proteger um agente OpenAI

`aeon.adapters.openai` usa duck typing: não importa o pacote `openai`, então funciona com o cliente real, dicts e dublês de teste. O laço de ferramentas não muda, só que as chamadas passam por um `ToolBox`.

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
    """Lê um arquivo de texto."""
    return f"contents of {path}"


@box.tool
def delete_file(path: str) -> str:
    """Apaga um arquivo."""
    return f"deleted {path}"

# client = OpenAI()   # lê OPENAI_API_KEY
messages = [{"role": "user", "content": "Resuma notes.txt"}]
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

- `tool_specs(box)` monta as definições de ferramenta do Chat Completions a partir dos seus type hints e docstrings. Passe `api="responses"` para a Responses API.
- `run_tool_calls(msg, box)` roda cada chamada pelo gate e devolve mensagens `role: tool` (ou itens `function_call_output` na Responses API). Uma chamada negada volta como o texto `Æon blocked this action: ...`, para o modelo se recuperar. Nada ali levanta exceção por ação bloqueada, ferramenta desconhecida ou argumentos malformados.
- `record_usage` soma o total de tokens da resposta ao monitor de orçamento.

O repositório tem uma versão executável com um cliente falso roteirizado, sem rede: `python examples/openai_agent/main.py`.

!!! warning "O que é protegido"
    O gate vê a chamada de ferramenta, não o texto do modelo. Um modelo que responde com texto nocivo sem chamar ferramenta não é impedido. Veja [Limites conhecidos](../known-limits.md).
