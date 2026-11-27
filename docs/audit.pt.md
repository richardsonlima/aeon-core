# Auditoria do aeon-core antes da reescrita v0.5.0

Data: 2026-11-27. Commit auditado: `b6c8706` (branch `develop`, mesma árvore da tag `v0.4.0-ULTRA` mais merges). A versão em inglês, [audit.md](audit.md), é a referência.

## O que existia

| Área | Estado em `b6c8706` |
|---|---|
| Pacote | `src/aeon/`, 90 arquivos, cerca de 7.250 linhas de Python em 25 subpacotes. |
| Empacotamento | `pyproject.toml` com hatchling, versão `0.4.0`, `requires-python >=3.9` enquanto os classificadores e o README diziam 3.10+. |
| Dependências | 17 dependências obrigatórias no núcleo, incluindo `openai`, `playwright`, `fastapi`, `uvicorn`, `sqlalchemy`, `beautifulsoup4`. |
| CLI | `src/aeon/cli/main.py` (Typer) com `init`, `run`, `serve`. **Sem entrada em `[project.scripts]`**, então o `aeon` não era instalado. |
| Testes | **Nenhum.** |
| CI | Um workflow que publicava no PyPI em qualquer tag `v*`, sem testes, lint nem checagem de tipos. |
| Documentação | Sete arquivos markdown no topo. O `README.md` apontava para um `README_pt.md` que não existia. Sem CHANGELOG. |
| Licença | Apache-2.0. Mantida. |

## O que funcionava (executado em 2026-11-27)

- `import aeon` funciona.
- `uv run aeon --help` falha: não havia script de console.
- Sem suíte de testes, nada mais pode ser chamado de "funcionando" com evidência.

## O que faltava

`aeon.axioms.axiom` e `enforce`, níveis de autonomia, kill-switch, modo shadow, baseline e orçamento, catálogo de falhas e campanhas, log de auditoria encadeado e `aeon audit verify`, `aeon doctor`, benchmarks, `claims.yaml` e página de limites conhecidos.

## O que contradizia as regras de honestidade

Linguagem de certificação ("SIL-4", "DO-178C", "IEC 61508 CERTIFIED") e "production-ready" sem testes nem evidência, em 22 linhas do repositório. No site público: `response_time_ms=0.1` sem medição, `sig=ed25519:ok` sem assinatura implementada, e `from aeon import Agent, ChaosBudget` com `ChaosBudget` inexistente.

## Decisões

1. **Reescrever, não refatorar** (ADR [001](decisions/001-rewrite-v0.5.md)). O código da v0.4.0 continua na tag `v0.4.0-ULTRA`.
2. **Os conflitos com o site ficam fora do escopo do código.** As mudanças necessárias estão em [Mudanças no site](site-changes.md).
3. **`aeon-axioms` independente** vira o subpacote `aeon.axioms`, sem dependências. Uma distribuição separada não foi construída.
