# Æon Core

O Æon é um runtime Python gratuito e de código aberto que **controla as ações de agentes LLM** e **injeta falhas controladas** para verificar se eles falham de forma segura.

Você envolve a função pela qual o agente executa ferramentas. Antes de cada chamada, um gate pequeno e síncrono decide: seguir, alertar, limitar ou bloquear. Depois da chamada, um caminho assíncrono grava um log de auditoria encadeado por hash e compara o agente com a sua própria baseline. Campanhas de caos então quebram coisas de propósito (um timeout, uma saída de ferramenta envenenada, um 429) e informam se o gate pegou, com falsos positivos e falhas impressos ao lado dos acertos.

*Inspirado no framework MECADE (engenharia do caos para confiabilidade); um projeto independente, sem relação com nenhum programa acadêmico.*

!!! warning "Status: alfa, v0.5.0 em desenvolvimento"
    Alfa, publicado no PyPI como `aeon-core`. O gate, a cadeia de auditoria, o orçamento, o catálogo de falhas, as campanhas, os adaptadores, o runtime e os servidores MCP estão implementados e testados. Registros de auditoria assinados, uma âncora externa para a cadeia, um backend Postgres e qualquer teste contra um LLM real **não foram construídos**. Leia [Limites conhecidos](known-limits.md) antes de depender dele.

## Comece aqui

<div class="grid cards" markdown>

- **[Instalação](get-started/install.md)** e o **[início rápido de 5 minutos](get-started/quickstart.md)**
- **[Prompt para um agente de código](get-started/coding-agent.md)** que liga o Æon usando só comandos documentados
- **[Gate e caminho de observação](concepts/gate.md)**: o que roda quando, e por que a divisão
- **[Adoção shadow-first](concepts/shadow-first.md)**: shadow, depois `ALERT`, `LIMIT`, `BLOCK`

</div>

## O que você recebe

| | |
|---|---|
| **Gate** | Regras `@axiom` e `enforce(executor)`. Falha segura: se uma regra ou o gate levantar exceção, a ação é bloqueada em modo enforce. Kill-switch e [Safe State](concepts/safe-state.md) por agente. |
| **Modo shadow** | O padrão. Todo veredito é registrado, nenhum é aplicado. |
| **Cadeia de auditoria** | Somente de acréscimo, encadeada por hash, escrita fora do caminho de decisão. `aeon audit verify` acha o primeiro elo quebrado. |
| **Orçamento** | Baseline por agente, score de desvio, CUSUM e um envelope absoluto. [A matemática](concepts/budget.md). |
| **Caos** | Oito falhas com guarda de raio de impacto, [campanhas](guides/campaigns.md) pré-registradas, intervalos de Wilson, execuções de controle. |
| **Adaptadores** | Python simples, OpenAI, Anthropic, LangGraph. Duck typing: nenhum SDK é importado. |
| **Runtime** | Serviço FastAPI local, painel de controle, servidores MCP para o gate e para esta documentação. |

## Evidências, com as más notícias

Todo número desta documentação vem de resultados versionados de uma máquina (Apple M1, Python 3.10.21, 2026-11-27), e cada página diz isso. Eles descrevem só aquela máquina.

- Uma decisão do gate: p99 de 15,0 µs com 10 axiomas, mas a pior chamada da execução foi 195 µs, e a fila de auditoria descartou 2.081 de 50.000 eventos num teste de rajada.
- De nove campanhas pré-registradas (oito enforce, uma shadow), **oito não atingiram a hipótese**: seis por falsos positivos (de 20% a 70% das execuções de controle limpas do agente simulado dispararam o alarme) e duas na verificação de Safe State. Nas campanhas enforce em que uma ação destrutiva foi tentada, nenhuma rodou.

Veja [Benchmarks](evidence/benchmarks.md), [Alegações](claims.md) e o [primeiro resultado desfavorável](blog/first-unfavourable-result.md).

## Escopo honesto

- O gate só cobre ações que passam pelo executor envolvido.
- Axiomas não julgam a correção semântica de texto livre.
- Injeção de caos não substitui um safety case. Não há certificação de nenhum tipo; normas como IEC 61508 ou DO-178C são, no máximo, inspiração e roteiro, não alegadas.

Licença: Apache-2.0. Código: [github.com/richardsonlima/aeon-core](https://github.com/richardsonlima/aeon-core). Sou Richardson Lima, e escrevo esta documentação em primeira pessoa quando importa.
