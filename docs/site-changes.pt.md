# Mudanças no site (para revisão)

Mudanças que o site público em `richardsonlima.com.br/aeon` precisa para refletir o que o código faz. Não editei o repositório do site. Cada item diz o que está errado, por quê, e o que colocar no lugar.

| # | No site | Problema | Trocar por |
|---|---|---|---|
| 1 | Exemplo de axioma `@axiom(on_violation="BLOCK", response_time_ms=0.1)` | `axiom` não tem argumento `response_time_ms`, e nenhuma medição versionada sustentava 0,1 ms. O número medido numa máquina é p99 de 15,0 a 15,4 µs e máximo de 81 µs com 10 axiomas, mas com 100 axiomas o máximo foi 134 µs e com 1 axioma 195 µs, acima de 0,1 ms, então um limite rígido de 0,1 ms não é sustentado. | Tire o argumento, ou escreva o número medido com o contexto: "p99 15,4 µs, máx 81 µs, 10 axiomas, Apple M1, Python 3.10.21, 2026-11-27", com link para [Benchmarks](evidence/benchmarks.md). |
| 2 | Linha de amostra de auditoria terminando em `sig=ed25519:ok` | Assinatura não está implementada. O registro tem `seq`, `ts`, `type`, `data`, `prev` e `hash` (sha256). | Remova `sig=...`. Mostre uma linha real de `aeon audit tail`, por exemplo `6 2026-11-27T13:41:14.962Z BLOCK default/delete_file DENIED (enforce) - Destructive tools need explicit approval.`. Se assinatura for citada, diga "roteiro, não construída". |
| 3 | Quickstart `from aeon import Agent, ChaosBudget` | `Agent` não existe. `ChaosBudget` existe e é alias de `Budget`. | Use o quickstart baseado em enforce: `from aeon.axioms import axiom, enforce`, envolva o executor com `enforce`, depois `aeon run agent.py` (veja o [início rápido](get-started/quickstart.md)). Mantenha `ChaosBudget(p99_ms=300, error_rate=0.02)` só onde o orçamento é o assunto, dizendo que equivale a `Budget(...)`. |
| 4 | `aeon serve` | Funciona, e agora é um alias documentado de `aeon runtime start`. | Mantenha, e cite o canônico `aeon runtime start`. Precisa de `pip install "aeon-core[runtime]"`. |
| 5 | `aeon.yaml` | O arquivo de configuração é `aeon.toml` (ou `[tool.aeon]` no `pyproject.toml`). | Troque `aeon.yaml` por `aeon.toml` e mostre um trecho TOML de [Configuração](reference/config.md). |
| 6 | "aeon-axioms, um módulo independente" | Não há distribuição separada. O motor de axiomas é o subpacote `aeon.axioms` do `aeon-core`, sem dependências de terceiros. | Diga "o subpacote `aeon.axioms` do `aeon-core`, sem dependências", e não mande ninguém fazer `pip install aeon-axioms`. |
| 7 | Sem link para a documentação | A documentação agora existe. | Adicione um link visível para `https://www.richardsonlima.com.br/aeon/docs/`, e para [Limites conhecidos](known-limits.md) e [Alegações](claims.md). |
| 8 | Qualquer texto com SIL, DO-178C, IEC 61508 ou "pronto para produção" | O código não tem certificação nem dados de campo, e a auditoria da v0.4 achou o mesmo tipo de texto no repositório antigo. | Use só "inspirado em" ou "roteiro", e diga alfa. Veja a [auditoria](audit.md). |
| 9 | Instruções de instalação | A 0.5.0 está no PyPI; a 0.3.0 e a 0.4.0 de lá são a linha antiga. | Mostre `pip install aeon-core` e diga que a 0.5.0 é uma reescrita com outra API. |

Não consegui ver o código-fonte atual do site ao escrever esta lista. Os itens 1, 2 e 3 vêm da [auditoria](audit.md), os outros da comparação dos nomes públicos do site com o código. Confira cada um na página publicada antes de editar.
