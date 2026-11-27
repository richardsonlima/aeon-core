# Escrever um axioma

Um axioma é uma função sobre um `Action` que diz se a ação é aceitável.

```python
from aeon.axioms import axiom, Violation, ALERT


@axiom(on_violation="BLOCK")
def no_destructive_tool_call(action):
    """Ferramentas destrutivas precisam de aprovação explícita."""
    return action.tool not in {"delete_file", "drop_table"} or action.approved


@axiom(on_violation="ALERT", tools=["http_get"])
def flag_external_urls(action):
    url = str(action.args.get("url", ""))
    return not url or url.startswith("https://internal.example.com")


@axiom(on_violation="LIMIT")
def big_transfers_need_approval(action):
    if action.tool == "transfer_funds" and action.args.get("amount", 0) > 100:
        return Violation("transfer above 100", level=ALERT if action.approved else None)
    return True
```

## O que a função pode devolver

| Retorno | Significado |
|---|---|
| `True` ou `None` | passa |
| `False` | objeta no nível declarado; o motivo é a primeira linha da docstring, ou `<nome> returned False` |
| um `str` | objeta no nível declarado, com esse texto como motivo |
| um `Violation(reason, level=None)` | objeta, e pode escolher o nível a cada chamada |
| uma exceção | o axioma é tratado como achado `BLOCK` (falha segura) |
| qualquer outra coisa | `TypeError`, também tratado como `BLOCK` de falha segura |

O `Action` traz `tool`, `args`, `agent`, `approved` e `context` (o que você anexar: o pedido do usuário, o número do passo, o ambiente). `tools=[...]` limita a regra a esses nomes de ferramenta.

## Mantenha axiomas pequenos e sintáticos

Eles rodam no caminho de decisão, na thread de quem chamou. Não faça E/S nem chame um modelo dentro de um axioma. Eles olham nomes de ferramenta e valores de argumento; não julgam se um texto livre está correto ou seguro. Veja [Limites conhecidos](../known-limits.md).

## Fábricas prontas

`aeon.axioms.builtin` devolve regras prontas. Atribua-as no nível do módulo de um arquivo de axiomas para o `aeon axioms list` encontrá-las:

```python
from aeon.axioms.builtin import (
    allow_tools,
    deny_arg_pattern,
    deny_tools,
    rate_limit,
    require_approval,
)

no_delete = deny_tools(["delete_file"], unless_approved=True)  # BLOCK
only_these = allow_tools(["read_file", "search_docs"])  # BLOCK para qualquer outra ferramenta
no_secrets = deny_arg_pattern(r"AKIA[0-9A-Z]{16}", level="BLOCK")  # regex sobre args de texto
deploys = require_approval(["deploy"])  # LIMIT sem aprovação
slow_down = rate_limit(30, 60, tools=["send_email"])  # LIMIT após 30 chamadas em 60 s
```

`rate_limit` usa tempo de relógio e conta decisões, então uma chamada negada também conta. É inadequado para um agente simulado rápido: as campanhas o deixam de fora de propósito.

## Carregar de um arquivo

Aponte `axioms = ["aeon_axioms.py"]` no `aeon.toml` para o arquivo. Confira antes de confiar:

```bash
aeon axioms list aeon_axioms.py
aeon axioms check aeon_axioms.py    # importa o arquivo e o autotesta com uma ação de sonda
```

Para testar um axioma em unidade, chame-o com um `Action`; o decorador devolve sua função intacta.
