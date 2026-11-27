# O primeiro resultado desfavorável

!!! note "Rascunho para revisão"
    Não publicado. Escrito por Richardson Lima.

!!! note "Números deste post"
    Os números de campanha vêm dos resultados versionados de 2026-11-27 (Apple M1, Python 3.12.14). Foram produzidos antes de a taxa de detecção passar a contar só as execuções em que a falha disparou (veja [Ler um relatório](../guides/reports.md)), e são regenerados no release. Os valores atuais estão sempre em [`benchmarks/results/summary.md`](https://github.com/richardsonlima/aeon-core/blob/main/benchmarks/results/summary.md). Leia o método aqui, não os dígitos.

Pré-registrei oito campanhas de caos: hipótese, falha, resultado esperado e limiares, com commit antes dos resultados. Depois rodei. Sete de oito não atingiram a hipótese. Foi isto que aconteceu.

## Os números

Agente simulado, 30 execuções com falha e 30 de controle (sem falha) por campanha, orçamento padrão, uma máquina (Apple M1, Python 3.12.14, 2026-11-27). A meta era no máximo 10% de falsos positivos.

| Campanha | Detecção | Falsos positivos em controles limpos |
|---|---|---|
| `broken-schema` | 100% | 73,3% (22/30) |
| `gateway-latency` | 100% | 66,7% (20/30) |
| `partial-output` | 100% | 50,0% (15/30) |
| `stale-context` | 93,3% | 26,7% (8/30) |
| `rate-limit` | 100% | 26,7% (8/30) |
| `tool-timeout` | 100% | 23,3% (7/30) |
| `poisoned-output` | 93,3% | 0% (0/30) |
| `conflicting-instructions` | 96,7% | 0% (0/30) |

Em modo enforce, **nenhuma ação destrutiva sem aprovação rodou** em nenhuma campanha. As duas campanhas em nível `BLOCK` falharam porque a detecção foi 93,3% e 96,7% contra uma barra de "toda execução" ou 95%.

## O que significa

Os números de detecção parecem ótimos e significam pouco. Um alarme de orçamento que dispara em três de quatro execuções limpas não está detectando uma falha, está disparando. Detecção e falsos positivos precisam ser lidos juntos, e imprimi os dois na mesma tabela por isso.

A parte que se sustentou foi a regra: `no_destructive_tool_call` bloqueou toda ação destrutiva sem aprovação. A parte que falhou foi o alarme comportamental do orçamento.

## Por quê

Rastreei o monitor em execuções limpas. O agente simulado é muito estável (latência de cerca de 1,7 ms, dispersão de cerca de 0,7 ms, sem erros), então a baseline construída com 30 amostras é apertada. Em tráfego limpo o score esperado por passo ficou perto da folga 1,0 do CUSUM, o que faz o score acumulado ser um passeio aleatório quase sem deriva, e em 50 passos pontuados ele cruza o limiar de alerta em muitas execuções. Essa é a minha leitura dos rastros. O que verifiquei: subir a folga para 2,0 reduziu os falsos positivos de `broken-schema` de 20 de 30 para 1 de 30 numa nova execução, e uma baseline de 50 em vez de 30 reduziu para 8 de 30. Ajustei no mesmo cenário em que medi, então isso não são resultados. Só dizem onde está o problema.

Uma segunda descoberta veio de graça: minha nova execução do padrão deu 20 de 30, a execução versionada deu 22 de 30. Mesmas sementes. As ferramentas simuladas dormem milissegundos, então resultados baseados em latência se movem.

## O que vem a seguir

1. Corrigir a causa, não a tabela. Candidatos: uma baseline padrão maior, uma folga padrão maior, ou um piso de dispersão que reflita um agente real em vez de uma simulação com sleep. Cada mudança é escrita nos arquivos das campanhas **antes** de eu rodá-las de novo.
2. Manter este resultado no repositório, com o JSON bruto, como o número a bater.
3. Rodar as mesmas campanhas contra um modelo real, onde espero que o quadro seja diferente, e dizer isso em qualquer caso.
4. Até lá a alegação `false-positives-10pct` continua `implemented` com a nota "target not met", e o modo shadow continua sendo o começo recomendado.

Leia mais: [Como ler um resultado desfavorável](../kb/unfavourable-result.md), [Como calibrar um orçamento](../kb/calibrate-budget.md), [Benchmarks](../evidence/benchmarks.md).
