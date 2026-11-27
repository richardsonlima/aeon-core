# Ferramentas MCP

O Æon fala MCP (JSON-RPC 2.0 delimitado por linha sobre stdio, versão de protocolo `2025-06-18`, e aceita `2025-03-26` e `2024-11-05`). Os logs vão para stderr, nunca para stdout, porque o stdout carrega o protocolo. Dois servidores:

## O gate: `aeon runtime mcp`

Monta um gate a partir da sua configuração e expõe quatro ferramentas. Adicione a um cliente MCP:

```json
{ "mcpServers": { "aeon": { "command": "aeon", "args": ["runtime", "mcp"] } } }
```

| Ferramenta | Argumentos | O que faz |
|---|---|---|
| `aeon_check_action` | `tool` (obrigatório), `args` (objeto), `agent`, `approved` | Pergunta ao gate se a ação pode rodar. Devolve o registro da decisão. **A ação não é executada.** |
| `aeon_status` | nenhum | Modo, kill-switch, Safe States, contadores, orçamento por agente e saúde da auditoria. |
| `aeon_audit_verify` | `expect_head` (hash opcional) | Verifica a cadeia de hashes do log de auditoria. |
| `aeon_run_campaign` | `target` (obrigatório, nome de falha ou de arquivo de campanha), `runs`, `controls`, `seed`, `blast_radius` | Roda uma campanha de caos contra o agente simulado e devolve resumo, verificações e resultados desfavoráveis. Limitada a 1000 execuções e 1000 passos; o teto de raio de impacto da sua configuração vale; caminhos de arquivo não são aceitos. |

Falhas esperadas voltam como resultado de ferramenta com `isError: true`, não como erro de protocolo.

Um cliente MCP não é o mesmo que um agente protegido. `aeon_check_action` só ajuda se o agente foi feito para perguntar antes de agir. O gate não intercepta ferramentas de um agente que não o chama.

## A documentação: `aeon docs mcp`

Serve a documentação. Ferramentas: `search_docs` (`query`, `limit` opcional de 1 a 20; devolve caminho, título e um trecho) e `read_doc` (`path`, um caminho `.md` relativo ou uma URI `aeon-docs://`). Recursos: todo `.md` do diretório de docs como `aeon-docs://<caminho relativo>`. Caminhos com `..`, caminhos absolutos e links simbólicos que saem do diretório de docs são rejeitados. `--docs-dir` aponta para outro diretório.

## Experimente à mão

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"t","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"aeon_check_action","arguments":{"tool":"delete_file"}}}' \
  | aeon runtime mcp
```
