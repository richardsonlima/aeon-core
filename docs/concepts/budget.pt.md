# Orçamento e desvio

Esta página é a matemática de `aeon.baseline`. Nada aqui foi ajustado para favorecer um resultado: os padrões produzem taxas altas de falso positivo no agente simulado (veja [Como ler um resultado desfavorável](../kb/unfavourable-result.md)).

Um **orçamento** responde: "quanto este agente pode se afastar do próprio comportamento normal?" Ele tem duas partes independentes: um score de desvio medido contra uma baseline calibrada, e um envelope absoluto que não precisa de calibração.

## 1. Calibração

Para cada agente, os primeiros `baseline_n` resultados (padrão 50) não são pontuados. Deles o Æon calcula:

| Símbolo | Significado |
|---|---|
| `m_L`, `s_L` | média e desvio padrão amostral (n-1) da latência em ms |
| `p_e` | fração de resultados que foram erro |
| `p_r` | fração que foram repetição (mesma ferramenta e mesmo digest de argumentos que uma das últimas `repeat_lookback` ações, padrão 3) |
| `m_T`, `s_T` | média e desvio padrão de tokens, se ao menos 2 resultados informaram tokens |
| `q` | contagem de chamadas por ferramenta (a distribuição de ferramentas) |

Durante a calibração o score é 0 e nenhum nível de desvio é levantado. Também dá para definir a baseline direto (`Monitor.set_baseline`) ou passá-la na construção.

## 2. Score de desvio por resultado

Cada resultado `t` seguinte recebe termos, cada um um z-score unilateral truncado em `[0, z_max]` com `z_max=10`:

```text
clip(z)=max(0,min(z_max,z))
```

- Latência, com piso no desvio para que uma baseline muito estável não faça qualquer oscilação parecer enorme:
  `sigma_L=max(s_L, 0.1 m_L, 1 ms)`, `z_lat=clip((x_t-m_L)/sigma_L)`.
- Erro e repetição são binários. Com `b_t in {0,1}` e taxa-base `p`:
  `z=clip((b_t-p)/sqrt(max(p(1-p), 0.01)))`.
- Tokens (só se o resultado e a baseline têm tokens):
  `sigma_T=max(s_T, 0.1 m_T, 1)`, `z_tok=clip((T_t-m_T)/sigma_T)`.
- Deriva (drift), quando a janela móvel (últimos `window`, padrão 50) tem ao menos `min_samples` resultados (padrão 20): a divergência de Jensen-Shannon (base 2, portanto em [0, 1]) entre a distribuição de ferramentas da baseline e a da janela, escalada:
  `z_drift=clip(JS(q_base,q_window)/drift_scale)`, `drift_scale` padrão 0,1.

Só conta desvio para cima. Mais rápido que o normal, menos erros que o normal: zero.

O score do passo é a soma ponderada, com pesos `w_k` (padrão 1 cada):

```text
d_t = sum over k of (w_k * z_k)
```

## 3. Acúmulo: CUSUM

O score do passo não é comparado direto a um limiar. Ele alimenta um CUSUM unilateral com folga `k` (`slack`, padrão 1,0):

```text
S_t = max(0, S_(t-1) + d_t - k)
```

`S_t` cresce enquanto o comportamento fica acima do normal e diminui `k` por passo quando não fica. O nível é o maior limiar cruzado:

| Condição | Nível |
|---|---|
| `S_t >=` `block_at` (padrão 20) | `BLOCK` |
| `S_t >=` `limit_at` (padrão 10) | `LIMIT` |
| `S_t >=` `alert_at` (padrão 5) | `ALERT` |
| caso contrário | `GO` |

Os limiares precisam satisfazer `0 <= alert_at <= limit_at <= block_at`. Um limiar 0 fica desligado.

Uma consequência direta das fórmulas: com `p_e=0`, um erro dá `z=1/sqrt(0.01)=10`, o truncamento, então `d_t >= 10` e `S` salta pelo menos 9. Um erro sozinho cruza `alert_at`, dois seguidos cruzam `limit_at`, três cruzam `block_at`. É o esperado para agentes que nunca falham. É também por isso que uma baseline sem erros é sensível.

## 4. O envelope absoluto

Independente da calibração, sobre a mesma janela móvel:

| Campo | Estoura quando | Precisa de |
|---|---|---|
| `p99_ms` | p99 por posto mais próximo das latências da janela `>` valor (ordenadas, índice `ceil(0.99 n)-1`) | `min_samples` resultados na janela |
| `error_rate` | fração de erros na janela `>` valor | `min_samples` resultados na janela |
| `max_cost` | custo acumulado `>` valor | nada |
| `max_tokens` | tokens acumulados `>` valor (inclui `record_usage`) | nada |

Um estouro leva o nível a `on_breach` (padrão `LIMIT`) se for maior que o nível de desvio. Campos deixados em `None` não são verificados. Os motivos ficam no achado, por exemplo `p99 latency 12.0 ms > 10 ms`.

## 5. Caminho de decisão e caminho de observação

`Monitor.record` (observação) faz tudo isso e guarda o nível resultante. `Monitor.finding` (decisão) só lê esse nível guardado, então uma decisão nunca calcula um z-score.

## 6. Semântica do reset

`Monitor.reset_accumulated(agent)` zera `S`, limpa a janela móvel e zera os totais de custo e tokens. A baseline calibrada é mantida. `Gate.reset(agent)` o chama ao liberar um agente do [Safe State](safe-state.md). Depois de um reset, os campos do envelope que precisam de `min_samples` ficam em silêncio até a janela encher de novo.

## Configuração

```toml
[aeon.budget]
baseline_n = 50
alert_at = 5.0
limit_at = 10.0
block_at = 20.0
p99_ms = 300       # envelope opcional
error_rate = 0.02
```

Todas as chaves estão em [Configuração](../reference/config.md). Para escolher valores, leia [Como calibrar um orçamento](../kb/calibrate-budget.md).
