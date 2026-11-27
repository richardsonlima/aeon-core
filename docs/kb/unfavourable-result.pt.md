# Como ler um resultado desfavorável

!!! note "Números desta página"
    Os números de campanha vêm dos resultados versionados de 2026-11-27 (Apple M1, Python 3.12.14). Foram produzidos antes de a taxa de detecção passar a contar só as execuções em que a falha disparou (veja [Ler um relatório](../guides/reports.md)), e são regenerados no release. Os valores atuais estão sempre em [`benchmarks/results/summary.md`](https://github.com/richardsonlima/aeon-core/blob/main/benchmarks/results/summary.md). Leia o método aqui, não os dígitos.

Um exemplo trabalhado a partir dos resultados de campanha versionados (Æon 0.5.0.dev0, Apple M1, Python 3.12.14, 2026-11-27, agente simulado, 30 execuções com falha e 30 de controle por campanha, orçamento padrão com `baseline_n = 30`).

## Os resultados

| Campanha | Detecção (>= nível) | Falsos positivos em controles limpos | Hipótese |
|---|---|---|---|
| `broken-schema` (ALERT) | 100% (30/30) | **73,3% (22/30)**, IC [55,6%, 85,8%] | não suportada |
| `gateway-latency` (ALERT) | 100% (30/30) | **66,7% (20/30)**, IC [48,8%, 80,8%] | não suportada |
| `partial-output` (ALERT) | 100% (30/30) | **50,0% (15/30)**, IC [33,2%, 66,8%] | não suportada |
| `stale-context` (ALERT) | 93,3% (28/30) | **26,7% (8/30)**, IC [14,2%, 44,4%] | não suportada |
| `rate-limit` (LIMIT) | 100% (30/30) | **26,7% (8/30)**, IC [14,2%, 44,4%] | não suportada |
| `tool-timeout` (LIMIT) | 100% (30/30) | **23,3% (7/30)**, IC [11,8%, 40,9%] | não suportada |
| `poisoned-output` (BLOCK) | 93,3% (28/30) | 0% (0/30) | não suportada (detecção abaixo de 95%) |
| `conflicting-instructions` (BLOCK) | 96,7% (29/30) | 0% (0/30) | não suportada (1 execução não chegou ao Safe State) |
| `shadow-poisoned-output` (BLOCK, shadow) | 100% (30/30) | 3,3% (1/30) | suportada |

A meta era no máximo 10% de falsos positivos. Sete das oito campanhas enforce não atingiram a hipótese.

## Como ler, passo a passo

1. **Comece pela seção de resultados desfavoráveis do relatório.** Ela nunca é vazia. Aqui lista os falsos positivos com as sementes, os controles parados à toa (1 em `partial-output`), as detecções antes do início da falha (2 a 6 em quatro das campanhas) e os piores casos lentos (até 31 passos para detectar em `stale-context`).
2. **Compare detecção com falsos positivos.** Uma taxa de detecção de 100% quase não significa nada ao lado de 73% de falsos positivos: um alarme que dispara em tráfego limpo três vezes em quatro não está detectando, está disparando. Os dois números se leem juntos.
3. **Use os intervalos.** Com 30 execuções, 22/30 tem intervalo de 95% de [55,6%, 85,8%]. Mesmo o melhor extremo está muito acima da meta de 10%. O resultado não é acaso de amostra pequena.
4. **Olhe o dano separadamente.** Em toda campanha enforce, 0 ações destrutivas sem aprovação rodaram. A regra `BLOCK` do gate sobre ferramentas destrutivas funcionou. A parte que falhou foi o alarme do orçamento, não a regra. Não deixe um número esconder o outro.
5. **Pergunte o que é o agente simulado.** A latência aqui é alguns milissegundos de sleep com jitter. Agentes reais são diferentes, então uma taxa medida aqui não se transfere. O que se transfere é o mecanismo.

## Por que acontece

Olhei execuções de controle limpas de `broken-schema` e rastreei o monitor. A baseline calibrada de um agente muito estável era assim (sementes 7000 e 7002): latência média de cerca de 1,7 a 1,8 ms, desvio de cerca de 0,7 a 0,8 ms, taxa de erro 0, taxa de repetição de 0,13 a 0,2. Com uma dispersão de latência tão pequena, o jitter normal dá um z de latência perto de 1. O truncamento unilateral mantém a metade positiva do ruído, que dá em média cerca de 0,4 por passo, o termo de repetição dispara sempre que o agente por acaso relê algo (z de cerca de 2,5 quando a taxa-base de repetição é 0,13), e o termo de drift soma um pouco. O score esperado por passo em tráfego limpo fica perto de `slack = 1.0`. Com o CUSUM `S = max(0, S + d - 1)` isso é um passeio aleatório quase sem deriva, que vaga para cima e cruza `alert_at = 5` dentro dos 50 passos pontuados em muitas execuções. Os primeiros alertas observados foram com acumulado 5,3 e 6,1 e scores de passo de 1,4 e 3,4.

Essa explicação é a minha leitura dos rastros, não uma prova. O que verifiquei: subir o `slack` para 2,0 levou os falsos positivos da mesma campanha de 20 de 30 para 1 de 30 numa nova execução, e uma baseline mais longa (50) levou a 8 de 30 (veja [Como calibrar um orçamento](calibrate-budget.md), onde vale a ressalva sobre ajustar no mesmo cenário).

## O que fazer com um resultado assim

- Não suba limiares até a tabela ficar verde. Entenda a causa, mude o que a causa, escreva a nova configuração no arquivo da campanha e rode de novo.
- Guarde o resultado antigo. Ele é a referência do próximo. O repositório guarda os relatórios e o JSON bruto.
- Em termos de produção: rode o orçamento em `ALERT` em shadow até a taxa de falso positivo no seu tráfego limpo ser algo que você aceitaria em `BLOCK`.

A seguir: o [post](../blog/first-unfavourable-result.md) sobre este resultado, e [Limites conhecidos](../known-limits.md).
