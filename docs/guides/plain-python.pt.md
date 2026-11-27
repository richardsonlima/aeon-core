# Proteger um agente Python simples

Qualquer agente que roda ferramentas por uma única função pode ser protegido envolvendo essa função. Esta é a integração inteira.

## 1. Envolva o executor

```python
from aeon.axioms import ActionBlocked, axiom, enforce

DESTRUCTIVE = {"delete_file", "drop_table", "send_email"}


@axiom(on_violation="BLOCK")
def no_destructive_tool_call(action):
    """Ferramenta destrutiva só roda com aprovação humana."""
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

O `enforce` escolhe como ler uma ação a partir da assinatura da função, uma vez, quando você a envolve:

| Assinatura | A ação é |
|---|---|
| primeiro parâmetro chamado `action` | o `Action` que você passa |
| dois primeiros parâmetros no formato `(tool, args)` (também `tool_name`, `name`, e `arguments`, `input`, `tool_input`, `params`) | nome da ferramenta e args desses parâmetros |
| qualquer outra | a própria função é a ferramenta, seus argumentos ligados são os args |

Passe `tool="nome"`, `agent="id"` ou `to_action=` para sobrescrever. O `enforce` também funciona em `async def` e como decorador.

## 2. Rode em shadow, depois em enforce

Sem configuração o gate fica em modo shadow e grava em `.aeon/audit.jsonl`. Rode pela CLI; sem `--mode` ela usa o modo do `aeon.toml` (shadow se não houver), e `--mode` o sobrescreve:

```bash
aeon run agent.py                  # shadow: delete_file roda, o veredito BLOCK é registrado
aeon run agent.py --mode enforce   # enforce: delete_file é bloqueado
aeon audit tail
aeon audit verify
```

## 3. Use um `ToolBox` quando tiver muitas ferramentas

`aeon.adapters.ToolBox` registra funções comuns e roteia toda chamada pelo gate:

```python
from aeon.adapters import ToolBox

box = ToolBox(gate=gate, agent="support-bot")

@box.tool
def read_file(path: str) -> str: ...

box.call("read_file", {"path": "notes.txt"})      # levanta ActionBlocked se negado
box.safe_call("read_file", {"path": "notes.txt"}) # devolve texto para o modelo em vez de levantar
```

## 4. Dê nome aos agentes

O campo `agent` define a [baseline](../concepts/budget.md) e o [Safe State](../concepts/safe-state.md). Dê a cada agente um nome estável, ou eles dividirão uma baseline.
