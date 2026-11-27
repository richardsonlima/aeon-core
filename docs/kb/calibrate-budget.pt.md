# Como calibrar um orçamento

O [orçamento](../concepts/budget.md) precisa de números que sirvam para o seu agente. Os padrões (`slack 1.0`, `alert_at 5`, `limit_at 10`, `block_at 20`, `baseline_n 50`) não são uma recomendação: no agente simulado produziram taxas altas de falso positivo. Calibre com o seu próprio tráfego limpo.

## Procedimento

1. **Colete um período limpo de baseline em shadow.** O orçamento precisa de `baseline_n` resultados por agente antes de pontuar qualquer coisa. Calibre durante a operação normal. Uma baseline tirada durante um incidente faz o incidente parecer normal.
2. **Observe o score no tráfego limpo.** `GET /v1/status` (ou `aeon_status`, ou `Gate.status()`) informa por agente `calibrated`, `deviation`, `accumulated`, `max_accumulated` e `level`. No tráfego limpo, `max_accumulated` é até onde o CUSUM vagou sem nada errado.
3. **Defina limiares acima disso, com margem.** `alert_at` deve ficar acima do maior `max_accumulated` visto em tráfego limpo. Depois espalhe `limit_at` e `block_at` mais para cima.
4. **Aumente o `slack` se o score sobe no tráfego limpo.** `S` ganha `d_t - slack` a cada passo. Se o `d_t` médio limpo está perto do `slack`, `S` vaga. Aumentar o `slack` faz ele escoar.
5. **Use o envelope para limites rígidos.** `p99_ms`, `error_rate`, `max_cost`, `max_tokens` não precisam de calibração. Defina `p99_ms` pelo p99 observado com margem, e lembre que a janela (padrão 50) é pequena, então um p99 de 50 amostras fica perto do máximo.
6. **Valide com controles.** Escreva uma [campanha](../guides/campaigns.md) com execuções de controle e um `max_false_positive_rate` que você aceita, e rode com `--runs 30 --controls 30` ou mais.
7. **Pré-registre de novo após ajustar.** Se você mudou o orçamento porque uma campanha falhou, o resultado antigo deixa de valer. Escreva os novos limiares no arquivo da campanha antes de rodar outra vez.

## O que vi no agente simulado

Uma execução exploratória na campanha `broken-schema`, 30 controles a cada vez, mesmas sementes. **Não** é um resultado: ajustei no mesmo cenário em que medi, e o cenário não é um LLM. Só mostra quais botões importam.

| Orçamento | Detecção | Falsos positivos nos controles |
|---|---|---|
| `baseline_n = 30` (ajuste da campanha) | 100% | 67% (20 de 30) |
| `baseline_n = 50` | 100% | 27% (8 de 30) |
| `baseline_n = 30`, `slack = 2.0` | 100% | 3% (1 de 30) |
| `baseline_n = 30`, `slack = 2.0`, limiares dobrados | 90% | 0% (0 de 30) |

Duas coisas a notar. Uma baseline mais longa ajudou muito, porque 30 amostras de um agente muito estável dão uma estimativa ruim da dispersão dele. E a primeira linha, 20 de 30, difere do resultado versionado da mesma campanha, 22 de 30: o agente simulado dorme alguns milissegundos por chamada, então resultados baseados em latência variam entre execuções mesmo com sementes fixas.

## Armadilhas

- Uma baseline com exatamente zero erros faz um erro valer z de 10. Está correto para um agente que nunca falha e ruidoso para um que às vezes falha.
- Agentes muito rápidos (latência abaixo de 1 ms) batem no piso de 1 ms do desvio de latência, então a maior parte do termo de latência vem do piso, não dos seus dados.
- O `reset` depois do Safe State limpa a janela e os totais, então as verificações de p99 e taxa de erro ficam quietas até chegarem `min_samples` resultados de novo.
