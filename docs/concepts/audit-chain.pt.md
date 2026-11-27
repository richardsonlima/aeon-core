# Cadeia de auditoria

O log de auditoria é somente de acréscimo e encadeado por hash, para você saber depois se um registro foi alterado, removido ou reordenado.

## Formato do registro

Cada registro é um objeto JSON:

```json
{"seq": 6, "ts": "2026-11-27T13:41:14.962Z", "type": "decision", "data": {"...": "..."}, "prev": "<hash do registro 5>", "hash": "<sha256>"}
```

`hash` é o sha256 do JSON canônico (chaves ordenadas, sem espaços) de `seq`, `ts`, `type`, `data` e `prev`. `prev` é o hash do registro anterior, e `0` repetido 64 vezes para o primeiro. Os tipos incluem `decision`, `result`, `mode`, `kill_switch`, `safe_state`, `audit.gap` e `audit.backend_error`.

Por padrão só um digest dos argumentos (`args_sha256`) e os nomes dos argumentos são gravados. Use `include_args = true` para gravar os argumentos brutos, pensando no que isso coloca em disco.

## Verificando

```bash
aeon audit verify                       # sai com 1 e aponta o primeiro elo quebrado
aeon audit verify --file caminho.jsonl
aeon audit verify --expect-head <hash>  # também detecta remoção no fim
```

A verificação recalcula todos os hashes e confere `seq` e `prev`. Ela para no primeiro elo quebrado e informa a linha e o número de sequência. Na execução versionada verificou cerca de 179 mil registros por segundo (uma máquina, veja [Benchmarks](../evidence/benchmarks.md)).

## O que detecta e o que não detecta

| Alteração | Detectada |
|---|---|
| um registro editado | sim, hash não confere |
| um registro removido do meio | sim, lacuna na sequência |
| registros reordenados | sim |
| uma linha corrompida | sim |
| registros removidos do **fim** | só com `--expect-head` e um hash de cabeça guardado em outro lugar |
| a cadeia inteira reconstruída por quem tem acesso de escrita | não |

Ainda não há assinatura nem âncora externa. Estão no roteiro, e não foram construídas. Até lá, copie o hash de cabeça para um lugar que quem escreve não alcance, se o log importar. Detalhes em [Limites conhecidos](../known-limits.md).

## Escrita fora do caminho de decisão

`emit` coloca o evento numa fila limitada (10.000 por padrão) e retorna. Uma thread de escrita sela e grava em lotes. Consequências:

- Se a fila encher, o evento é descartado, contado, e um registro `audit.gap` é escrito depois. No teste de rajada versionado (20.000 eventos sem pausa) 3.856 foram descartados. A 1.000 eventos/s nenhum foi.
- Se o armazenamento falhar, os registros esperam em memória (limitada), a thread tenta de novo com espera crescente e, quando o armazenamento volta, ela escreve primeiro um registro `audit.backend_error`, então a queda fica na cadeia.
- Acréscimos JSONL são tudo ou nada: se uma escrita ou fsync falhar, o lote parcial é truncado. Uma quebra de linha final ausente é reparada quando o arquivo é reaberto, e arquivos novos são criados com modo `0600`.
- Um processo de escrita por arquivo de log. Dois processos acrescentando ao mesmo arquivo bifurcam a cadeia.

## Backends

JSONL (padrão, `.aeon/audit.jsonl`), SQLite (`sqlite:.aeon/audit.db` ou um caminho `.db`) e um backend em memória para testes. `aeon audit tail` (`-n 0` não imprime nada) e `aeon audit export --format jsonl|csv` leem qualquer um. A exportação CSV neutraliza células que começam como fórmulas de planilha. Não há backend Postgres.
