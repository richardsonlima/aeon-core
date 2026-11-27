# Æon Core

[English](https://github.com/richardsonlima/aeon-core/blob/main/README.md) | [Português](https://github.com/richardsonlima/aeon-core/blob/main/README.pt.md)

![version](https://img.shields.io/badge/version-0.5.0-blue) ![license](https://img.shields.io/badge/license-Apache--2.0-green) ![python](https://img.shields.io/badge/python-3.10%2B-blue)

O Æon é um runtime Python gratuito e de código aberto que **controla as ações de agentes LLM** e **injeta falhas controladas** para verificar se eles falham de forma segura.

Você envolve a função pela qual o agente executa ferramentas. Antes de cada chamada, um gate pequeno e síncrono decide: seguir, alertar, limitar ou bloquear. Depois da chamada, um caminho assíncrono grava um log de auditoria encadeado por hash e compara o agente com a própria baseline. Campanhas de caos então quebram coisas de propósito (um timeout, uma saída de ferramenta envenenada, um 429) e informam se o gate pegou, com falsos positivos e falhas incluídos.

Inspirado no framework MECADE (engenharia do caos para confiabilidade); um projeto independente, sem relação com nenhum programa acadêmico.

## Status

**Alfa.** Instale com `pip install aeon-core`. É uma reescrita do zero da v0.4 (veja o [`CHANGELOG.md`](https://github.com/richardsonlima/aeon-core/blob/main/CHANGELOG.md) e a [auditoria](https://www.richardsonlima.com.br/aeon/docs/pt/audit/)).

| Implementado e testado | Não construído |
|---|---|
| Gate, axiomas, níveis de autonomia, Safe State, kill-switch, modo shadow | Registros de auditoria assinados e âncora externa para a cadeia |
| Log de auditoria encadeado por hash (JSONL, SQLite) e `aeon audit verify` | Backend de auditoria Postgres |
| Baseline de comportamento, score de desvio, CUSUM e envelope | Dados de campo, e uma taxa medida de qualquer coisa num LLM real |
| Oito falhas com guarda de raio de impacto, campanhas pré-registradas | Escritores de auditoria em vários processos |
| Adaptadores para Python simples, OpenAI, Anthropic e LangGraph (duck typing) | Certificação de qualquer tipo (IEC 61508, DO-178C e semelhantes são só inspiração e roteiro) |
| Runtime HTTP local, painel de controle, servidores MCP para o gate e para a documentação | Uma imagem de contêiner publicada |
| SDK de agentes: `Agent`, `Team`, `Workflow`, sessões, memória, aprovação, saída estruturada; roda em modelos reais (OpenRouter, OpenAI, Anthropic, Ollama) | Streaming de tokens, execução async, RAG ([roteiro](https://www.richardsonlima.com.br/aeon/docs/pt/roadmap/agent-sdk/)) |

**Leia os [Limites conhecidos](https://www.richardsonlima.com.br/aeon/docs/pt/known-limits/) antes de depender dele.** A versão curta: o gate só cobre ações que passam pelo executor envolvido, axiomas não julgam o significado de texto livre, e nas campanhas versionadas o orçamento padrão gerou falsos positivos em até 70% das execuções de controle limpas de um agente simulado (oito de nove hipóteses pré-registradas não foram suportadas).

## Instalação

Requer Python 3.10 ou mais novo. O núcleo não tem dependências de terceiros.

```bash
pip install aeon-core            # ou: pip install "aeon-core[runtime]" para o runtime HTTP
uv add aeon-core                 # num projeto
uvx --from aeon-core aeon version
pipx install aeon-core           # como ferramenta de linha de comando
```

As versões 0.3.0 e 0.4.0 no PyPI são a linha antiga; a 0.5.0 é uma reescrita com outra API.

## Início rápido

```bash
mkdir my-agent && cd my-agent
aeon init            # grava aeon.toml (modo shadow) e aeon_axioms.py
aeon doctor
```

Salve como `agent.py`:

```python
from aeon.axioms import ActionBlocked, enforce


@enforce
def run_tool(tool, args):
    return {
        "read_file": lambda path: f"contents of {path}",
        "delete_file": lambda path: f"deleted {path}",
    }[tool](**args)


for tool, args in [("read_file", {"path": "notes.txt"}), ("delete_file", {"path": "prod.db"})]:
    try:
        print(tool, "->", run_tool(tool, args))
    except ActionBlocked as exc:
        print(tool, "-> blocked:", exc)
```

```bash
aeon run agent.py                  # shadow: delete_file roda, o veredito BLOCK é registrado
aeon run agent.py --mode enforce   # enforce: delete_file é bloqueado
aeon audit tail
aeon audit verify                  # ok: 8 records, chain intact
aeon chaos run "poisoned output" --runs 10 --controls 10
```

Comece em modo shadow, leia o log e mova uma regra por vez para `ALERT`, `LIMIT` e depois `BLOCK`.

## Desenvolvimento

```bash
git clone https://github.com/richardsonlima/aeon-core && cd aeon-core
uv sync --group dev --extra runtime
uv run --no-sync pytest
```

O [`CONTRIBUTING.md`](https://github.com/richardsonlima/aeon-core/blob/main/CONTRIBUTING.md) (em inglês) tem todas as verificações do CI (lint, tipos, testes, smoke do pacote, auditoria de dependências, docs), os benchmarks, como rodar o painel de controle na porta 8787 e as regras de branches, commits e alegações.

## Documentação

- Docs: <https://www.richardsonlima.com.br/aeon/docs/pt/> (português e inglês; também `docs/` neste repositório, `aeon docs mcp` para servi-la a um agente de código, e o [`llms.txt`](https://github.com/richardsonlima/aeon-core/blob/main/llms.txt))
- [Início rápido de 5 minutos](https://www.richardsonlima.com.br/aeon/docs/pt/get-started/quickstart/) e um [prompt para um agente de código](https://www.richardsonlima.com.br/aeon/docs/pt/get-started/coding-agent/)
- [Alegações](https://www.richardsonlima.com.br/aeon/docs/pt/claims/): cada alegação com o status da evidência
- [Limites conhecidos](https://www.richardsonlima.com.br/aeon/docs/pt/known-limits/)
- [Benchmarks](https://github.com/richardsonlima/aeon-core/blob/main/benchmarks/README.md): como reproduzir, o que não significam, e os resultados desfavoráveis. Todo número descreve uma máquina apenas.
- [Segurança](https://www.richardsonlima.com.br/aeon/docs/pt/security/) e [`SECURITY.md`](https://github.com/richardsonlima/aeon-core/blob/main/SECURITY.md)
- [Contribuindo](https://github.com/richardsonlima/aeon-core/blob/main/CONTRIBUTING.md), [Guia de release](https://github.com/richardsonlima/aeon-core/blob/main/RELEASE.md), [Changelog](https://github.com/richardsonlima/aeon-core/blob/main/CHANGELOG.md)

## Licença

Apache-2.0. Veja [`LICENSE`](https://github.com/richardsonlima/aeon-core/blob/main/LICENSE).
