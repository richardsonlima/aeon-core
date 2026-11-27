# Instalação

!!! warning "Ainda não está no PyPI"
    Nenhuma versão foi publicada. Os comandos marcados como "após a primeira versão" não funcionam hoje. Até lá, instale de um checkout ou do git. A `main` remota ainda é a linha antiga v0.4 e a `feature/v0.5.0` ainda não foi enviada, então instale de um checkout local do trabalho da v0.5.0.

Requer Python 3.10 ou mais novo. O núcleo não tem dependências de terceiros (só `tomli` no 3.10).

## De um checkout (funciona hoje)

```bash
cd aeon-core                       # seu checkout do trabalho da v0.5.0
```

=== "pip"

    ```bash
    python -m venv .venv && . .venv/bin/activate
    pip install .                  # só o núcleo
    pip install ".[runtime]"       # mais o runtime HTTP
    aeon version
    ```

=== "uv"

    ```bash
    uv venv && uv pip install .
    uv run aeon version
    ```

=== "uvx"

    ```bash
    uvx --from /caminho/para/aeon-core aeon version
    ```

=== "pipx"

    ```bash
    pipx install /caminho/para/aeon-core
    aeon version
    ```

Quando a branch estiver no GitHub, o mesmo funciona direto do git: `pip install "aeon-core @ git+https://github.com/richardsonlima/aeon-core@<branch>"`, `uvx --from "git+https://github.com/richardsonlima/aeon-core@<branch>" aeon version`, `pipx install "git+https://github.com/richardsonlima/aeon-core@<branch>"`.

## Após a primeira versão

```bash
pip install aeon-core
uv add aeon-core                      # num projeto
uvx --from aeon-core aeon version     # sem instalar
pipx install aeon-core                # como ferramenta de linha de comando
```

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
