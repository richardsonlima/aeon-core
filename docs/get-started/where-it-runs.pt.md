# Onde roda

O Æon é uma biblioteca Python e uma ferramenta de linha de comando. Ele roda onde rodam as chamadas de ferramenta do seu agente, porque o gate é uma chamada de função na frente da ferramenta.

| Onde | Como | Observações |
|---|---|---|
| **Local**, qualquer agente Python | `pip install aeon-core`, envolva o executor com `enforce` | Sem servidor, sem rede, sem conta. A auditoria vai para um arquivo local. |
| **Local, outras linguagens ou processos** | `aeon runtime start` e chame `POST /v1/actions/evaluate` | Precisa do extra `runtime`. Loopback por padrão. Veja [Runtime](../guides/runtime.md). |
| **Agentes de código (MCP)** | `aeon runtime mcp` para o gate, `aeon docs mcp` para a documentação | Transporte stdio. |
| **Docker** | `docker compose up --build` a partir do repositório | Construído localmente; nenhuma imagem é publicada. Veja [Runtime](../guides/runtime.md). |
| **CI** | `aeon chaos run <campanha> --strict` | Reprova o build quando uma hipótese não é suportada. Veja [gate no CI](../guides/ci-gate.md). |
| **LangGraph, OpenAI, Anthropic** | `aeon.adapters` | Duck typing; o SDK é seu. Veja os guias. |

## O que precisa

- Python 3.10 ou mais novo.
- Um lugar gravável para o log de auditoria (padrão `.aeon/audit.jsonl`), ou `audit = "off"`.
- Mais nada para o núcleo. Sem dependências, sem telemetria, sem conta. Veja [Segurança](../security.md).

## O que não faz

- Não chama um modelo. As campanhas usam um agente simulado com roteiro.
- Não executa suas ferramentas pelo runtime. O runtime só decide.
- Um escritor de auditoria por arquivo de log, um gate por processo. Vários processos no mesmo arquivo de auditoria bifurcam a cadeia. Veja [Limites conhecidos](../known-limits.md).
