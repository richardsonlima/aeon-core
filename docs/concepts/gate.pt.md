# Gate e caminho de observação

O Æon divide o trabalho em dois caminhos, de propósito.

| | Caminho de decisão | Caminho de observação |
|---|---|---|
| Pergunta | Esta ação pode rodar agora? | O que aconteceu, e o agente está se desviando? |
| Código | `Gate.decide` | `Gate.observe`, `Monitor.record`, thread de escrita do `AuditLog` |
| Roda | de forma síncrona, na thread de quem chamou | depois da ação, e em thread de fundo para a auditoria |
| Pode fazer | ler memória, chamar suas funções de axioma, ler um nível de orçamento em cache | calcular hash, escrever arquivos, calcular baselines, atualizar métricas |
| Nunca faz | E/S, rede, esperar um lock preso pelo caminho de observação | bloquear o caminho de decisão |

## O caminho de decisão

`Gate.decide(action)` nunca levanta exceção e usa só a biblioteca padrão. Para uma ação, ele faz isto, nesta ordem:

1. Se o **kill-switch** estiver acionado, adiciona um achado `BLOCK`.
2. Se o agente estiver em **Safe State** e o gate estiver em modo `enforce`, adiciona um achado `BLOCK`.
3. Executa todo axioma que se aplica à ferramenta. O axioma devolve `True` ou `None` para passar, `False` ou um texto de motivo para objetar no nível declarado, ou um `Violation` para escolher o nível a cada chamada. Um axioma que levanta exceção conta como achado `BLOCK`.
4. Lê o nível de orçamento **em cache** do agente no `Monitor` (sem calcular nada aqui) e adiciona um achado se estiver acima de `GO`.
5. O veredito é o nível mais alto entre os achados (`GO` se não houver nenhum).

O que o veredito faz depende do modo:

| Modo | `GO`, `ALERT` | `LIMIT` | `BLOCK` |
|---|---|---|---|
| `shadow` | roda | roda, veredito registrado | roda, veredito registrado |
| `enforce` | roda | roda só se a ação estiver `approved` ou o gancho de aprovação disser sim | não roda, o agente entra em [Safe State](safe-state.md) |

O kill-switch é a exceção: vale nos dois modos.

Se o próprio gate falhar (um bug, não uma regra), o veredito é `BLOCK`: em `enforce` a ação não roda, em `shadow` ela roda e o erro é registrado. O mesmo vale para um axioma que levanta exceção. É a regra de falha segura, coberta por testes (veja [Alegações](../claims.md), `fail-closed`).

`enforce(executor)` envolve um callable para que toda chamada passe por `decide` antes. Uma chamada negada levanta `ActionBlocked` (`ActionLimited` para um `LIMIT` sem aprovação, `SafeStateActive` quando o agente já estava retido) e o executor não é chamado.

## O caminho de observação

Depois que o executor retorna ou levanta exceção, `Gate.observe` registra o resultado: latência, ok ou erro, tokens e custo. Isso alimenta a [baseline de comportamento e o orçamento](budget.md) e enfileira um evento de auditoria.

O log de auditoria nunca escreve na thread de quem chamou. `emit` carimba o evento e o coloca numa fila limitada; uma thread de escrita sela os registros na [cadeia de hashes](audit-chain.md) e os grava. Se a fila encher, o evento é descartado e contado, e a cadeia registra depois um evento `audit.gap`. O caminho de decisão nunca espera.

## Quanto custa

Na execução de benchmark versionada (Apple M1, Python 3.12.14, 2026-11-27, auditoria desligada) um `decide` levou p50 de 10 a 12 µs com 1 a 10 axiomas e p99 de 12,6 µs com 10 axiomas. Com 100 axiomas o p99 foi 41,9 µs e a pior chamada 462,6 µs. Com o log JSONL ligado, o p99 subiu para 187 µs e a pior chamada para 3,7 ms. Esses números descrevem só aquela máquina. As tabelas completas, com p99 e máximo, estão em [Benchmarks](../evidence/benchmarks.md).

## O limite do gate

O gate só cobre ações que passam pelo executor envolvido. Um agente que chega a uma ferramenta por outro caminho não é protegido. Veja [Limites conhecidos](../known-limits.md).
