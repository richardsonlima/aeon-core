# Construir um agente

O `aeon.agents` constrói e roda agentes de LLM cujas chamadas de ferramenta passam todas pelo gate. Não precisa de SDK de provedor: os clientes usam só a biblioteca padrão. Uma chamada bloqueada volta ao modelo como texto, um `BLOCK` põe o agente em Safe State e para o loop, e toda decisão vai para o log de auditoria.

## O menor agente

```python
from aeon.agents import Agent
from aeon.axioms import Gate
from aeon.axioms.builtin import deny_tools


def read_file(path: str) -> str:
    """Read a text file and return its contents."""
    return open(path).read()


def delete_file(path: str) -> str:
    """Delete a file permanently."""
    ...


agent = Agent(
    "openrouter:openai/gpt-4o-mini",
    tools=[read_file, delete_file],
    gate=Gate([deny_tools(["delete_file"])], mode="enforce"),
    instructions="You are an ops assistant. Use the tools.",
)
agent.print_response("Summarise notes.txt")
```

Ferramentas são funções simples: a assinatura vira o JSON schema e a primeira linha da docstring vira a descrição. `run()` devolve um `RunOutput` com `content`, `status` (`completed`, `paused`, `stopped`), `stop_reason`, `tool_calls` (cada uma com `blocked`), `tokens`, `duration_s` e as `messages` completas.

## Modelos

`model` é `provedor:modelo`. A chave vem do ambiente.

| Provedor | Exemplo | Chave |
|---|---|---|
| OpenRouter | `openrouter:openai/gpt-4o-mini` | `OPENROUTER_API_KEY` |
| OpenAI | `openai:gpt-4o-mini` | `OPENAI_API_KEY` |
| Anthropic | `anthropic:claude-haiku-5.5` | `ANTHROPIC_API_KEY` |
| Groq | `groq:llama-3.1-8b-instant` | `GROQ_API_KEY` |
| Ollama | `ollama:qwen2.5:3b` | nenhuma |
| Qualquer servidor Chat Completions | `resolve_model("compatible:m", base_url=...)` | `OPENAI_API_KEY`, opcional |

Também dá para passar um cliente de SDK oficial: `Agent("gpt-4o-mini", tools, client=openai.OpenAI())`. Os campos de raciocínio que o provedor devolve (`reasoning_details`) voltam sem alteração.

## Aprovação humana

Uma regra `require_approval` transforma a ferramenta num `LIMIT`: a execução pausa em vez de rodá-la.

```python
from aeon.axioms.builtin import require_approval

agent = Agent(model, [delete_file], gate=Gate([require_approval(["delete_file"])], mode="enforce"))
run = agent.run("Delete prod.db")
if run.status == "paused":
    print([c.name for c in run.pending])  # ['delete_file']
    run = agent.continue_run(run, approve=True)  # ou approve={"delete_file": False}
```

`approval="deny"` recusa sem pausar; `approval=lambda call: ...` decide na hora. O sim vale só para aquela chamada.

## Sessões e memória

```python
from aeon.agents import SqliteDb

agent = Agent(
    model,
    db=SqliteDb("agents.db"),
    add_history_to_context=True,  # turnos anteriores da sessão
    num_history_runs=3,
    enable_agentic_memory=True,  # uma ferramenta update_user_memory, atrás do gate
    add_datetime_to_context=True,
)
agent.run("I prefer short answers", session_id="s1", user_id="rick")
agent.run("What do I prefer?", session_id="s2", user_id="rick")  # pela memória
```

O banco guarda prompts e respostas em texto puro: mantenha o arquivo privado.

## Saída estruturada

```python
from dataclasses import dataclass


@dataclass
class Report:
    revenue: int
    costs: int


run = Agent(model, [read_file], output_schema=Report).run("Fill the report from q3.txt")
run.content  # Report(revenue=120, costs=80)
```

Serve uma dataclass, um modelo Pydantic ou um dict de JSON schema. Uma resposta inválida ganha uma nova tentativa; a segunda para a execução com `stop_reason="bad_output"`.

## Eventos, debug e chat no terminal

```python
for event in agent.run("...", stream=True):
    print(event.event, event.data)  # RunStarted, ModelRequestCompleted, ToolCallBlocked, ...
```

`debug=True` (ou `AEON_DEBUG_AGENT=1`) mostra cada etapa no stderr. `agent.cli_app()` é um chat no terminal que pede as aprovações no prompt.

## Times e workflows

```python
from aeon.agents import Step, Team, Workflow

bull = Agent(model, name="Bull", role="Make the case for.")
bear = Agent(model, name="Bear", role="Make the case against.")
team = Team([bull, bear], model, instructions="Hear both, then recommend.")
team.print_response("Should we adopt a monorepo?")

flow = Workflow([Step("Debate", team=team), Step("Brief", agent=writer)])
flow.run("Should we adopt a monorepo?").content
```

Um membro do time é uma ferramenta do coordenador (`delegate_to_bull`), então um axioma pode negar uma delegação e o kill-switch para o time inteiro. Um workflow para no primeiro passo que não conclui.

## Pela linha de comando

```bash
export OPENROUTER_API_KEY=...
aeon agent run "Read notes.txt and do what it says." --tools tools.py \
  --model openai/gpt-4o-mini --mode enforce
```

As ferramentas são as funções públicas de `tools.py` (ou a lista `TOOLS` dele); o gate vem do `aeon.toml`. Veja o [exemplo](https://github.com/richardsonlima/aeon-core/tree/main/examples/agent_sdk) e o [roteiro](../roadmap/agent-sdk.md).
