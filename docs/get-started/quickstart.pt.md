# Início rápido (5 minutos)

Você vai proteger um agente minúsculo, ver o gate registrar o que bloquearia (shadow), ligar o bloqueio (enforce), verificar o log de auditoria e rodar uma campanha de caos. Instale primeiro: [Instalação](install.md).

## 1. Crie a estrutura e confira

```bash
mkdir my-agent && cd my-agent
aeon init
aeon doctor
```

`aeon init` grava `aeon.toml` (em modo `shadow`) e `aeon_axioms.py` com axiomas de exemplo. `aeon doctor` deve terminar com `All checks passed.` e a linha `gate self-test: block, Safe State, shadow, fail-closed, kill-switch and audit chain all behave`.

```bash
aeon axioms list
```

```text
BLOCK  no_destructive_tool_call  Destructive tools need explicit approval.
ALERT  flag_external_urls        Record calls that reach outside the company domain.
LIMIT  require_approval          require approval  [tools: deploy]
```

## 2. Proteja um agente

Salve como `agent.py`:

```python
from aeon.axioms import ActionBlocked, enforce


@enforce
def run_tool(tool, args):
    return {"read_file": lambda path: f"contents of {path}",
            "delete_file": lambda path: f"deleted {path}"}[tool](**args)


for tool, args in [("read_file", {"path": "notes.txt"}), ("delete_file", {"path": "prod.db"})]:
    try:
        print(tool, "->", run_tool(tool, args))
    except ActionBlocked as exc:
        print(tool, "-> blocked:", exc)
```

Os axiomas vêm de `aeon_axioms.py`, que o `aeon.toml` carrega. Rode em modo shadow, depois em enforce:

```bash
aeon run agent.py
```

```text
read_file -> contents of notes.txt
delete_file -> deleted prod.db
[aeon] mode=shadow decisions=2 allowed=2 denied=0 gate_errors=0
```

```bash
aeon run agent.py --mode enforce
```

```text
read_file -> contents of notes.txt
delete_file -> blocked: Æon blocked 'delete_file' (BLOCK): Destructive tools need explicit approval.
[aeon] mode=enforce decisions=2 allowed=1 denied=1 gate_errors=0
```

Em shadow, `delete_file` rodou, e o log diz que ele teria sido bloqueado.

## 3. Leia e verifique o log de auditoria

```bash
aeon audit tail
aeon audit verify
```

```text
     2 2026-11-27T13:41:14.914Z BLOCK default/delete_file allowed (shadow) - Destructive tools need explicit approval.
     6 2026-11-27T13:41:14.962Z BLOCK default/delete_file DENIED (enforce) - Destructive tools need explicit approval.
     7 2026-11-27T13:41:14.962Z safe_state {"entered": true, "agent": "default", ...}
ok: 8 records, chain intact
head 815b18c7...
```

Altere um registro e verifique de novo:

```bash
cp .aeon/audit.jsonl copy.jsonl && sed -i.bak 's/delete_file/read_file/' copy.jsonl
aeon audit verify --file copy.jsonl
```

```text
BROKEN at line 3, seq 2: hash mismatch: record content was changed
2 records verified before the break
```

O código de saída é 1. A remoção no fim só é detectada com `--expect-head`; veja [Cadeia de auditoria](../concepts/audit-chain.md).

## 4. Injete uma falha

```bash
aeon chaos list
aeon chaos run "poisoned output" --runs 10 --controls 10
```

```text
[staging] fault poisoned-output injected from step 40 in 10 runs (10 controls)
  escalation (first run): BLOCK · Safe State reached
  detection 100%  false positives 20%  Safe State 100%  harmful actions executed 0
  hypothesis supported
```

Leia os números duas vezes: a detecção é 100%, e a taxa de falso positivo é 20%. O gate disparou o alarme em tráfego limpo do agente simulado em 2 de 10 execuções de controle. É o tipo de resultado que o Æon reporta de propósito; veja [Ler um relatório](../guides/reports.md).

## Próximos passos

- Proteja seu agente: [Python simples](../guides/plain-python.md), [OpenAI](../guides/openai.md), [Anthropic](../guides/anthropic.md), [LangGraph](../guides/langgraph.md).
- Fique um tempo em shadow: [Adoção shadow-first](../concepts/shadow-first.md).
- O que isto não cobre: [Limites conhecidos](../known-limits.md).
