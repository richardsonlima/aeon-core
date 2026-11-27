# Níveis de autonomia

Quatro níveis, em ordem de severidade. Um axioma declara o nível em que objeta (`on_violation`), e o veredito do gate é o nível mais alto entre todos os achados.

| Nível | Significado | Em `shadow` | Em `enforce` |
|---|---|---|---|
| `GO` | Nenhuma regra objetou. | roda | roda |
| `ALERT` | Registrar, nunca interferir. | roda, registrado | roda, registrado |
| `LIMIT` | Restringir: a ação precisa de aprovação. | roda, registrado | roda só se `approved`, ou se o gancho de aprovação devolver verdadeiro; senão `ActionLimited` |
| `BLOCK` | Parar a ação e reter o agente. | roda, registrado | não roda, `ActionBlocked`, o agente entra em [Safe State](safe-state.md) |

`GO` é um veredito, não algo que você declara: `@axiom(on_violation="GO")` é rejeitado.

## Aprovação

Uma ação está aprovada quando `Action.approved` é verdadeiro, o que o seu código define depois que uma pessoa diz sim. O gate também aceita um gancho `approver(decision) -> bool`, chamado só para um `LIMIT` aplicado. Um gancho que levanta exceção não aprova. Um `LIMIT` nunca leva o agente ao Safe State.

## De onde vêm os níveis

- Axiomas: `@axiom(on_violation="BLOCK")`, ou as fábricas de `aeon.axioms.builtin` (`deny_tools`, `allow_tools`, `rate_limit`, `deny_arg_pattern`, `require_approval`). Veja [Escrever um axioma](../guides/axioms.md).
- O orçamento: desvio acumulado cruzando `alert_at`, `limit_at` ou `block_at`, ou estouro do envelope em `on_breach`. Veja [Orçamento e desvio](budget.md).
- O kill-switch: sempre `BLOCK`.

## Subindo de nível

Não comece em `BLOCK`. O caminho é shadow, depois `ALERT`, depois `LIMIT`, depois `BLOCK` para as poucas regras em que você confia. Veja [Adoção shadow-first](shadow-first.md).
