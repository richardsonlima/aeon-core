# Benchmarks

Todo número abaixo vem dos arquivos versionados em [`benchmarks/results/`](https://github.com/richardsonlima/aeon-core/tree/main/benchmarks/results). As tabelas desta página são geradas desses arquivos por `scripts/gen_reference.py`, então não podem se afastar dos dados.

**Estes números descrevem uma máquina apenas.** Não leia como promessa para a sua. Para medir a sua: `python benchmarks/run_all.py` (`--quick` para um teste rápido). Veja o [README dos benchmarks](https://github.com/richardsonlima/aeon-core/blob/main/benchmarks/README.md) para o que cada um mede e o que não significa.

<!-- BEGIN GENERATED: machine -->
Máquina e execução: Apple M1, Darwin 25.6.0, CPython 3.10.21, 8 CPUs; Æon 0.5.0.dev0; run 2026-11-27T14:21:21Z. Estes números descrevem só essa máquina.
<!-- END GENERATED: machine -->

## Latência de decisão do gate

Uma chamada `Gate.decide`, só o caminho de decisão, auditoria desligada, GC do Python ligado para as pausas aparecerem no p99 e no máximo. Tempos em µs.

<!-- BEGIN GENERATED: gate -->
µs por `Gate.decide`, auditoria desligada, 100000 amostras por linha (10000 de aquecimento descartadas).

| Axiomas | Modo | Monitor | p50 | p90 | p99 | máx |
|---|---|---|---|---|---|---|
| 1 | shadow | on | 11.9 | 12.6 | 13.1 | 135.0 |
| 1 | enforce | on | 11.9 | 12.4 | 13.2 | 195.0 |
| 10 | shadow | on | 14.1 | 14.2 | 15.0 | 81.2 |
| 10 | enforce | on | 14.1 | 14.5 | 15.4 | 80.7 |
| 100 | shadow | on | 35.2 | 36.1 | 38.1 | 117.8 |
| 100 | enforce | on | 35.8 | 36.3 | 38.2 | 133.9 |
| 1 | enforce | off | 11.9 | 12.1 | 12.5 | 53.1 |
<!-- END GENERATED: gate -->

Leia a coluna do máximo. A mediana é de 12 a 36 µs conforme o número de axiomas, e chamadas isoladas na execução levaram até 195 µs. A latência também cresce com o número de axiomas que se aplicam: o p99 é 15,0 µs com 10 axiomas e 38,1 µs com 100.

## Auditoria

Custo no caminho de decisão, atraso até durabilidade e velocidade de verificação. "Lag durável" é o tempo entre o `emit` e o registro ser gravado. "Descartados" são eventos que não couberam na fila de 10.000 eventos; cada descarte é informado depois como um registro `audit.gap`.

<!-- BEGIN GENERATED: audit -->
| Cenário | emit p50 µs | emit p99 µs | emit máx µs | descartados | lag durável p50 ms | lag p99 ms | lag máx ms |
|---|---|---|---|---|---|---|---|
| rajada de 50000 eventos, sem pausa | 2.33 | 3.33 | 76697 | 2081 de 50000 | 55.1 | 137.7 | 199.0 |
| ritmado a 1000/s | 2.50 | 20.71 | 91 | 0 de 5000 | 4.1 | 16.9 | 30.7 |
| ritmado a 500/s com fsync | 2.62 | 21.04 | 30 | 0 de 2000 | 22.3 | 36.0 | 44.8 |

`Gate.decide` sem auditoria: p50 11.8 µs, p99 12.4 µs, máx 65 µs. Com auditoria JSONL: p50 16.3 µs, p99 438.0 µs, máx 3399 µs. Verificação da cadeia: 159061 registros/s (47921 registros).
<!-- END GENERATED: audit -->

A linha da rajada é a desfavorável: 50.000 eventos sem pausa estouraram a fila e 2.081 foram descartados. A 1.000 eventos/s ritmados nenhum foi. Um emit na rajada travou por cerca de 77 ms, muito provavelmente por contenção com a thread de escrita. Com o log de auditoria ligado, `Gate.decide` teve p99 de 438 µs e pior chamada de 3,4 ms, contra 12,4 µs e 65 µs com ele desligado no mesmo arquivo: os máximos são ruído da máquina e não são reproduzíveis até o dígito.

## Campanhas de detecção

Campanhas pré-registradas no cenário simulado `ops-assistant`: um agente com semente e roteiro, **não um LLM**. 30 execuções com falha e 30 de controle cada. Os intervalos de confiança são intervalos de Wilson de 95%.

<!-- BEGIN GENERATED: detection -->
| Campanha | Nível | Detecção [IC 95%] | Falsos positivos [IC 95%] | Safe State | Ações nocivas executadas | Tempo até detectar (passos p50 / p90 / máx) | Hipótese |
|---|---|---|---|---|---|---|---|
| `broken-schema` (enforce) | ALERT | 100% [89, 100] | 70% [52, 83] | 0% | 0 | 6 / 10 / 13 | NÃO suportada |
| `conflicting-instructions` (enforce) | BLOCK | 100% [88, 100] | 0% [0, 11] | 97% | 0 | 4 / 13 / 14 | NÃO suportada |
| `gateway-latency` (enforce) | ALERT | 100% [89, 100] | 67% [49, 81] | 10% | 0 | 1 / 1 / 2 | NÃO suportada |
| `partial-output` (enforce) | ALERT | 100% [89, 100] | 50% [33, 67] | 3% | 0 | 6 / 10 / 15 | NÃO suportada |
| `poisoned-output` (enforce) | BLOCK | 96% [82, 99] | 0% [0, 11] | 90% | 0 | 4 / 11 / 24 | NÃO suportada |
| `rate-limit` (enforce) | LIMIT | 100% [89, 100] | 27% [14, 44] | 27% | 0 | 2 / 5 / 16 | NÃO suportada |
| `shadow-poisoned-output` (shadow) | BLOCK | 100% [89, 100] | 3% [1, 17] | 0% | 385 | 2 / 13 / 20 | suportada |
| `stale-context` (enforce) | ALERT | 97% [83, 99] | 27% [14, 44] | 0% | 0 | 8 / 26 / 32 | NÃO suportada |
| `tool-timeout` (enforce) | LIMIT | 100% [89, 100] | 20% [10, 37] | 70% | 0 | 2 / 7 / 9 | NÃO suportada |
<!-- END GENERATED: detection -->

Oito das nove hipóteses **não foram suportadas**: todas as oito campanhas enforce, seis por falsos positivos (o orçamento padrão dispara o alarme em 20% a 70% das execuções de controle limpas) e duas na verificação de Safe State. As campanhas detectam as falhas. A detecção conta só execuções em que a falha disparou, e "nenhuma ação destrutiva sem aprovação rodou" só é evidência nas campanhas em que uma foi tentada. Os relatórios com cada resultado desfavorável estão em [`benchmarks/results/campaigns/`](https://github.com/richardsonlima/aeon-core/tree/main/benchmarks/results/campaigns). Uma leitura trabalhada está em [Como ler um resultado desfavorável](../kb/unfavourable-result.md).

## Como isso se relaciona com as alegações

[Alegações](../claims.md) lista cada alegação com o status. As marcadas `measured` apontam para estes arquivos, e uma alegação cuja medição não atingiu a meta diz isso lá (`false-positives-10pct`, pior taxa de falso positivo 73%).

## O que estes benchmarks não mostram

- Nada sobre um LLM real, uma rede real ou um agente em produção.
- Nada sobre outro hardware, outras versões do Python ou outros sistemas operacionais.
- Nada sobre comportamento de longa duração, crescimento de memória ou muitos agentes concorrentes.
- As latências das campanhas incluem sleeps nas ferramentas simuladas, então não são overhead do gate.
