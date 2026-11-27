# Safe State

Safe State é onde um agente fica retido depois de um `BLOCK` aplicado. É por agente (o campo `agent` da ação, `default` se você não definir).

## O que acontece

- O primeiro `BLOCK` aplicado de um agente registra um `SafeState` (motivo, id da decisão, hora) e emite um evento de auditoria `safe_state`.
- Enquanto o agente está retido, **toda** ação dele recebe um achado `BLOCK` do tipo `safe-state` em modo `enforce` e levanta `SafeStateActive`. Os axiomas continuam rodando, então a auditoria mostra por que cada ação também seria objetada.
- Outros agentes não são afetados.
- Um `LIMIT` nunca entra em Safe State.
- Em modo `shadow` nenhum agente entra em Safe State, porque nada é aplicado.

## Como sair

O Safe State não expira. Alguém o libera:

```python
gate.reset("my-agent")  # devolve True se o agente estava retido
```

ou `POST /v1/safe-state/{agent}/reset` no [runtime](../guides/runtime.md). Liberar também zera o desvio acumulado do agente, a janela móvel e os totais de custo e tokens (a baseline calibrada permanece). Um evento `safe_state` com `entered: false` é registrado.

## Kill-switch

O kill-switch é a parada do operador para todos: `gate.engage_kill_switch("motivo")` bloqueia toda ação de todo agente, em `shadow` e em `enforce`, até `gate.release_kill_switch()`. Como é aplicado, os agentes bloqueados também entram em Safe State. As duas chamadas são auditadas.

## O que Safe State não é

Não desfaz nada que o agente já fez, e não impede um agente de agir por um caminho que contorna o gate. Veja [O que o BLOCK garante](../kb/what-block-guarantees.md).
