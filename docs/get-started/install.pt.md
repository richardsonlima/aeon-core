# Instalação

Requer Python 3.10 ou mais novo. O núcleo não tem dependências de terceiros (só `tomli` no 3.10).

## Do PyPI

```bash
pip install aeon-core
pip install "aeon-core[runtime]"      # mais o runtime HTTP
uv add aeon-core                      # num projeto
uvx --from aeon-core aeon version     # sem instalar
pipx install aeon-core                # como ferramenta de linha de comando
```

As versões 0.3.0 e 0.4.0 no PyPI são a linha antiga do código. A 0.5.0 é uma reescrita com outra API: leia o [changelog](https://github.com/richardsonlima/aeon-core/blob/main/CHANGELOG.md) antes de atualizar.

## De um checkout

```bash
cd aeon-core
pip install .                  # ou: uv pip install . / pipx install .
```

Do git: `pip install "aeon-core @ git+https://github.com/richardsonlima/aeon-core@main"`.

## Extras

| Extra | Adiciona | Necessário para |
|---|---|---|
| `runtime` | `fastapi`, `uvicorn` | `aeon runtime start`, `aeon serve`, `aeon ui` |
| `openai` | `openai` | só se você usa o SDK da OpenAI; o adaptador não o importa |
| `anthropic` | `anthropic` | idem, para o SDK da Anthropic |
| `langgraph` | `langgraph`, `langchain-core` | idem, para o LangGraph |
| `all` | todos os anteriores | |

Exemplo com `runtime`: `pip install ".[runtime]"`.

## Confira

```bash
aeon version
aeon doctor
```

`aeon doctor` verifica a versão do Python, a configuração, os arquivos de axiomas, se o local de auditoria é gravável, verifica uma cadeia de auditoria existente e roda um autoteste do gate (bloqueio, Safe State, shadow, falha segura, kill-switch e cadeia de auditoria).

## Desenvolver no próprio Æon

```bash
uv sync --group dev --extra runtime
uv run --no-sync pytest
```

Veja o `CONTRIBUTING.md` no repositório. Para construir esta documentação: `uv sync --group docs --extra runtime && uv run --no-sync python scripts/gen_reference.py && uv run --no-sync mkdocs build --strict`.
