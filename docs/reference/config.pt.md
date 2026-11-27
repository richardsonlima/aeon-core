# Configuração

O Æon lê `aeon.toml` (ou `.aeon.toml`), ou uma tabela `[tool.aeon]` no `pyproject.toml`, e depois aplica as variáveis de ambiente `AEON_*`, que prevalecem. Chaves desconhecidas são rejeitadas com o nome do arquivo, então um erro de digitação falha alto.

## Onde o arquivo é encontrado

1. `AEON_CONFIG`, se definida (um caminho).
2. Senão, partindo do diretório atual e subindo: `aeon.toml`, `.aeon.toml`, depois um `pyproject.toml` que tenha `[tool.aeon]`. A busca para no diretório que contém `.git`.
3. Senão, os padrões. Caminhos relativos no arquivo (arquivos de axiomas, caminho de auditoria) são resolvidos a partir do diretório do arquivo. `--config <caminho>` na CLI escolhe um arquivo explicitamente.

## `aeon.toml`

```toml
[aeon]
mode = "shadow"                  # "shadow" (padrão) ou "enforce"
axioms = ["aeon_axioms.py"]      # um caminho ou uma lista; arquivos Python que declaram axiomas
include_args = false             # true grava os argumentos brutos das ferramentas na auditoria

[aeon.audit]
path = ".aeon/audit.jsonl"       # ou "sqlite:.aeon/audit.db", "memory" ou "off"
fsync = false                    # true torna cada lote durável antes de a escrita continuar

[aeon.budget]                    # toda chave de Budget, veja abaixo
baseline_n = 50
alert_at = 5.0
limit_at = 10.0
block_at = 20.0
# p99_ms = 300
# error_rate = 0.02

[aeon.chaos]
environment = "dev"
max_blast_radius = "staging"     # teto: "dev", "staging" ou "prod-shadow"
```

`audit` também pode ser uma string: `audit = ".aeon/audit.jsonl"`. Os valores `off`, `none`, `false`, `0` ou texto vazio desligam o log. `[aeon.runtime]` é aceita e guardada, e nada a lê ainda. `environment` fica no objeto de configuração e ainda não altera nenhuma decisão.

No `pyproject.toml`, escreva as mesmas tabelas sob `[tool.aeon]`, por exemplo `[tool.aeon.budget]`.

## Chaves do orçamento

Todas são opcionais. A matemática está em [Orçamento e desvio](../concepts/budget.md).

| Chave | Padrão | Significado |
|---|---|---|
| `p99_ms` | nenhum | envelope: latência p99 na janela |
| `error_rate` | nenhum | envelope: fração de erros na janela |
| `max_cost` | nenhum | envelope: custo acumulado |
| `max_tokens` | nenhum | envelope: tokens acumulados |
| `on_breach` | `LIMIT` | nível levantado por um estouro do envelope (`ALERT`, `LIMIT` ou `BLOCK`) |
| `baseline_n` | 50 | resultados usados para calibrar cada agente (mínimo 2) |
| `window` | 50 | tamanho da janela móvel |
| `min_samples` | 20 | resultados na janela antes de avaliar drift, p99 e taxa de erro |
| `slack` | 1.0 | folga `k` do CUSUM |
| `alert_at` | 5.0 | desvio acumulado para `ALERT` |
| `limit_at` | 10.0 | desvio acumulado para `LIMIT` |
| `block_at` | 20.0 | desvio acumulado para `BLOCK` |
| `z_max` | 10.0 | truncamento de cada z-score |
| `repeat_lookback` | 3 | quantas ações recentes definem uma repetição |
| `drift_scale` | 0.1 | divergência de Jensen-Shannon que vale z = 1 |
| `weights` | todos 1.0 | pesos por termo: `latency`, `error`, `repeat`, `tokens`, `drift` |

## Variáveis de ambiente

| Variável | Efeito |
|---|---|
| `AEON_CONFIG` | caminho do arquivo de configuração a usar |
| `AEON_MODE` | sobrescreve `mode` (`shadow` ou `enforce`) |
| `AEON_AUDIT` | sobrescreve o local da auditoria (`off` desliga) |
| `AEON_AXIOMS` | sobrescreve os arquivos de axiomas, separados pelo separador de caminho do SO (`:` em Linux e macOS) |
| `AEON_ENVIRONMENT` | sobrescreve `[aeon.chaos] environment` |
| `AEON_MAX_BLAST_RADIUS` | sobrescreve o teto do raio de impacto |
| `AEON_RUNTIME_TOKEN` | token bearer do [runtime](../guides/runtime.md); senão `.aeon/runtime.token` é usado e criado |
| `AEON_RUNTIME_ALLOWED_HOSTS` | lista de Hosts permitidos, separados por vírgula, para o runtime. Padrão em bind de loopback: `localhost`, `127.0.0.1`, `[::1]`. Vale em qualquer bind e em contêineres (o `compose.yaml` define `localhost,127.0.0.1`). Em bind fora do loopback sem ela, não há checagem de Host |
| `AEON_RUNTIME_ALLOW_REMOTE` | `1` permite escutar em endereço fora do loopback. Leia [Segurança](../security.md) antes |
| `AEON_DEBUG` | qualquer valor mostra o traceback Python em vez de um erro de uma linha na CLI |

`AEON_TELEMETRY` não faz nada: o Æon não envia telemetria, e o `aeon doctor` avisa se a variável estiver definida.

`aeon run <script> --mode enforce` define `AEON_MODE` para aquela execução. Sem `--mode`, o `aeon run` usa o modo configurado (`aeon.toml`, senão shadow).

## Confira

```bash
aeon doctor      # mostra o arquivo de configuração em uso, o modo, os axiomas e o local da auditoria
```
