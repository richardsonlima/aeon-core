# Roteiro: um SDK de agentes com o gate embutido

O Æon começou como a camada de controle entre um agente e as ferramentas dele. Esta página lista o que falta para ele ser também o SDK com que você constrói o agente: agentes, times e workflows, com sessões, memória e aprovação humana.

A diferença continua a mesma. No Æon, toda chamada de ferramenta de todo agente, membro de time e passo de workflow passa pelo gate: axiomas, níveis de autonomia, Safe State, kill-switch, orçamento e o log de auditoria encadeado por hash. Guardrails postos por cima de um loop podem ser pulados; aqui o loop não tem outro jeito de rodar uma ferramenta.

Legenda: **entregue** (numa versão, testado), **próximo** (em construção para a próxima versão), **planejado** (aceito, não começado), **fora do escopo** (não planejado; use outra ferramenta).

## Primitivas

| Capacidade | O que significa | Status | Como o Æon faz |
|---|---|---|---|
| Agent | Um modelo, ferramentas e instruções, e o loop entre eles | **entregue** (0.5.1) | `aeon.agents.Agent`; toda chamada de ferramenta por um `ToolBox` e pelo gate |
| String de modelo | `model="openrouter:openai/gpt-4o-mini"` em vez de montar um cliente | **entregue** (0.5.1) | `provedor:modelo` resolvido para os clientes HTTP da biblioteca padrão |
| Funções simples como ferramentas | `tools=[read_file, search]` | **entregue** (0.5.1) | envolvidas num `ToolBox` ligado ao gate do agente |
| Team | Um coordenador delega a agentes membros | **entregue** (0.5.1) | os membros viram ferramentas do coordenador, então a própria delegação passa pelo gate e pela auditoria |
| Workflow | Passos repetíveis sobre agentes, times e funções | **entregue** (0.5.1) | passos em sequência, a saída de um é a entrada do próximo; um passo parado para o workflow |

## Execução e saída

| Capacidade | Status | Notas |
|---|---|---|
| `run()` devolvendo um objeto de execução (conteúdo, mensagens, métricas, chamadas) | **entregue** (0.5.1) | `RunOutput`: `run_id`, `session_id`, `status`, `duration_s`, tokens |
| `print_response()` para desenvolvimento | **entregue** (0.5.1) | chamadas de ferramenta com o veredito, depois a resposta |
| Fluxo de eventos (início, chamada ao modelo, ferramenta iniciada, concluída, bloqueada, fim) | **entregue** (0.5.1) | eventos por etapa em `run(stream=True)` |
| Streaming de tokens | planejado | precisa ler Server-Sent Events por provedor |
| Saída estruturada (`output_schema`) | **entregue** (0.5.1) | JSON schema a partir de dataclass ou modelo Pydantic, validado, uma nova tentativa se o JSON vier errado |
| Async (`arun`) | planejado | o gate já aceita ferramentas async |
| CLI interativo (`cli_app`) | **entregue** (0.5.1) | `Agent.cli_app()` e `aeon agent chat` |
| Modo debug | **entregue** (0.5.1) | `debug=True` ou `AEON_DEBUG_AGENT=1` mostra mensagens e tokens por etapa |
| Modelos de raciocínio | **entregue** | os campos de raciocínio do provedor (`reasoning_details`) voltam sem alteração |

## Modelos

| Capacidade | Status | Notas |
|---|---|---|
| OpenAI, OpenRouter, Groq, vLLM, LM Studio, Ollama | **entregue** | `OpenAICompatible`, só biblioteca padrão |
| API Messages da Anthropic | **entregue** | `AnthropicClient`, também por gateways com autenticação bearer |
| Clientes dos SDKs oficiais | **entregue** | o loop usa duck typing: `openai.OpenAI()` e `anthropic.Anthropic()` funcionam |
| Modelos de reserva (fallback) | planejado | tentar o próximo modelo em caso de erro do provedor |
| Mais de 30 integrações nativas de provedores | fora do escopo | o OpenRouter e os servidores compatíveis cobrem a maioria por uma API só |

## Memória e contexto

| Capacidade | Status | Notas |
|---|---|---|
| Armazenamento de sessões (`db=SqliteDb(...)`, `session_id`) | **entregue** (0.5.1) | `sqlite3` da biblioteca padrão, sem dependência extra |
| Histórico no contexto (`add_history_to_context`, `num_history_runs`) | **entregue** (0.5.1) | |
| Memória do usuário (`enable_agentic_memory`, `user_id`) | **entregue** (0.5.1) | uma ferramenta `update_user_memory`, também atrás do gate |
| Estado da sessão | planejado | |
| Data e hora no contexto | **entregue** (0.5.1) | `add_datetime_to_context` |
| Knowledge (RAG sobre banco vetorial) | fora do escopo por ora | precisa de embeddings e de um banco vetorial; pode entrar como ferramenta |
| Compressão, aprendizado, provedores de contexto | fora do escopo por ora | |

## Controle e segurança

| Capacidade | Status | Notas |
|---|---|---|
| Guardrails nas chamadas de ferramenta | **entregue** | axiomas, regras prontas, níveis de autonomia; enforce ou shadow |
| Kill-switch e Safe State | **entregue** | o loop para antes da próxima chamada ao modelo |
| Orçamento de tokens e de comportamento | **entregue** | o uso de tokens de cada resposta alimenta o monitor |
| Auditoria à prova de adulteração de toda decisão | **entregue** | cadeia de hash, `aeon audit verify` |
| Injeção de falhas e campanhas | **entregue** | `aeon chaos`, campanhas pré-registradas |
| Aprovação humana (human-in-the-loop) | **entregue** (0.5.1) | uma regra `require_approval` pausa a execução; `continue_run(approve=...)` retoma |
| Guardrails de entrada e saída (texto) | planejado | hooks no prompt e na resposta |
| Hooks antes e depois da execução | planejado | |

## Operação

| Capacidade | Status | Notas |
|---|---|---|
| Gerador de projeto | planejado | `aeon create agent` grava um projeto de agente pronto para rodar |
| Servir agentes por HTTP | planejado | o runtime já serve o gate; agentes em seguida |
| Painel de controle | **entregue** para o gate | decisões, campanhas, auditoria e alegações em `/ui/` |
| Docs por MCP para agentes de código | **entregue** | `aeon docs mcp` |
| Observabilidade (OpenTelemetry) | planejado | |
| Evals | planejado | as campanhas já medem detecção e falsos positivos |
| Execução em segundo plano, agendador | fora do escopo por ora | |
| Entrada multimodal | fora do escopo por ora | |

## Evidência

O loop do agente rodou contra modelos reais pelo OpenRouter em 2026-11-27: `openai/gpt-4o-mini`, `anthropic/claude-haiku-5.5`, `qwen/qwen3-32b`, `meta-llama/llama-3.1-8b-instruct` e `google/gemini-2.5-flash-lite`, com o resultado de uma ferramenta mandando o modelo apagar um arquivo. Quatro modelos tentaram apagar e o gate bloqueou; um pediu confirmação ao usuário antes. O caminho da API Messages e um modelo de raciocínio (`openai/gpt-5-nano` com raciocínio ligado) também rodaram. São execuções únicas num só dia, não uma taxa medida: veja [Limites conhecidos](../known-limits.md).
