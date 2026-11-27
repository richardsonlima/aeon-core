# Referência da CLI

!!! info "Página gerada"
    Esta página é gerada por `scripts/gen_reference.py` a partir de `aeon.cli.main.build_parser()`. Não edite à mão; altere a fonte e rode o script de novo.


O comando `aeon` usa só a biblioteca padrão. Todo comando que imprime dados aceita `--json`. Falhas esperadas mostram uma mensagem e uma dica de correção e saem com código diferente de zero, sem stack trace. Códigos de saída: `0` ok, `1` falha (inclui campanha reprovada com `--strict` e cadeia de auditoria quebrada), `2` erro de uso. Os textos de ajuda abaixo vêm do código e estão em inglês.

## `aeon`

```text
usage: aeon [-h] [--config CONFIG] <command> ...
```

Gate the actions of LLM agents and check that they fail safe.

| Opção | Padrão | Descrição |
|---|---|---|
| `--config` |  | path to aeon.toml (default: discover from cwd) |

## `aeon doctor`

check environment, config, storage and run a gate self-test

```text
usage: aeon doctor [-h] [--json]
```

| Opção | Padrão | Descrição |
|---|---|---|
| `--json` |  | print JSON |

## `aeon init`

scaffold aeon.toml and example axioms (shadow mode)

```text
usage: aeon init [-h] [--json] [--force] [path]
```

| Opção | Padrão | Descrição |
|---|---|---|
| `--json` |  | print JSON |
| `path` | `.` | project directory (default: .) |
| `--force` |  | overwrite existing files |

## `aeon axioms`

list and validate axioms

```text
usage: aeon axioms [-h] <subcommand> ...
```

### `aeon axioms list`

list axioms from config or files

```text
usage: aeon axioms list [-h] [--json] [files ...]
```

| Opção | Padrão | Descrição |
|---|---|---|
| `--json` |  | print JSON |
| `files` |  |  |

### `aeon axioms check`

import an axiom file and self-test it

```text
usage: aeon axioms check [-h] [--json] file
```

| Opção | Padrão | Descrição |
|---|---|---|
| `--json` |  | print JSON |
| `file` |  |  |

## `aeon run`

run a Python agent script under the gate

```text
usage: aeon run [-h] [--mode {shadow,enforce}] script [script_args ...]
```

| Opção | Padrão | Descrição |
|---|---|---|
| `script` |  |  |
| `--mode` {shadow,enforce} |  | override the configured mode (default: from aeon.toml, else shadow) |
| `script_args` |  | arguments for the script, after `--` (aeon run a.py -- --flag) |

## `aeon chaos`

fault catalog and campaigns

```text
usage: aeon chaos [-h] <subcommand> ...
```

### `aeon chaos list`

list the fault catalog

```text
usage: aeon chaos list [-h] [--json]
```

| Opção | Padrão | Descrição |
|---|---|---|
| `--json` |  | print JSON |

### `aeon chaos run`

run a fault or a campaign file

```text
usage: aeon chaos run [-h] [--json] [--blast-radius {dev,staging,prod-shadow}] [--seed SEED]
                      [--runs RUNS] [--controls CONTROLS] [--mode {shadow,enforce}] [--markdown]
                      [--strict]
                      target
```

| Opção | Padrão | Descrição |
|---|---|---|
| `--json` |  | print JSON |
| `target` |  | fault name or alias (e.g. "degrade gateway latency"), campaign id, or campaign .toml |
| `--blast-radius` {dev,staging,prod-shadow} |  |  |
| `--seed` |  |  |
| `--runs` |  |  |
| `--controls` |  |  |
| `--mode` {shadow,enforce} |  |  |
| `--markdown` |  | also print the full report |
| `--strict` |  | exit 1 if the hypothesis is not supported (for CI) |

## `aeon report`

render a campaign report (markdown + JSON)

```text
usage: aeon report [-h] [--json] [-o OUTPUT] [campaign]
```

| Opção | Padrão | Descrição |
|---|---|---|
| `--json` |  | print JSON |
| `campaign` |  | campaign id or result .json; omit to list |
| `-o`, `--output` |  | write <output>.md and <output>.json |

## `aeon audit`

read and verify the audit log

```text
usage: aeon audit [-h] <subcommand> ...
```

### `aeon audit verify`

recompute the hash chain

```text
usage: aeon audit verify [-h] [--json] [--file FILE] [--expect-head EXPECT_HEAD]
```

| Opção | Padrão | Descrição |
|---|---|---|
| `--json` |  | print JSON |
| `--file` |  | audit log (default: from config) |
| `--expect-head` |  | fail unless the chain ends at this hash |

### `aeon audit tail`

show the last records

```text
usage: aeon audit tail [-h] [--json] [--file FILE] [-n N] [--type TYPE]
```

| Opção | Padrão | Descrição |
|---|---|---|
| `--json` |  | print JSON |
| `--file` |  |  |
| `-n` | `20` |  |
| `--type` |  | only records of this type (decision, result, ...) |

### `aeon audit export`

export records as JSONL or CSV

```text
usage: aeon audit export [-h] [--file FILE] [--format {jsonl,csv}] [-o OUTPUT]
```

| Opção | Padrão | Descrição |
|---|---|---|
| `--file` |  |  |
| `--format` {jsonl,csv} | `jsonl` |  |
| `-o`, `--output` |  |  |

## `aeon runtime`

local HTTP + MCP service (extra: runtime)

```text
usage: aeon runtime [-h] <subcommand> ...
```

### `aeon runtime start`

start the HTTP runtime

```text
usage: aeon runtime start [-h] [--host HOST] [--port PORT]
```

| Opção | Padrão | Descrição |
|---|---|---|
| `--host` | `127.0.0.1` |  |
| `--port` | `8787` |  |

### `aeon runtime mcp`

serve the gate over MCP (stdio)

```text
usage: aeon runtime mcp [-h]
```

## `aeon serve`

alias of `aeon runtime start`

```text
usage: aeon serve [-h] [--host HOST] [--port PORT]
```

| Opção | Padrão | Descrição |
|---|---|---|
| `--host` | `127.0.0.1` |  |
| `--port` | `8787` |  |

## `aeon ui`

open the control plane against a local runtime

```text
usage: aeon ui [-h] [--host HOST] [--port PORT] [--no-browser]
```

| Opção | Padrão | Descrição |
|---|---|---|
| `--host` | `127.0.0.1` |  |
| `--port` | `8787` |  |
| `--no-browser` |  |  |

## `aeon docs`

documentation tools

```text
usage: aeon docs [-h] <subcommand> ...
```

### `aeon docs mcp`

serve the docs over MCP (stdio) for coding agents

```text
usage: aeon docs mcp [-h] [--docs-dir DOCS_DIR]
```

| Opção | Padrão | Descrição |
|---|---|---|
| `--docs-dir` |  | docs directory (default: bundled docs) |

## `aeon version`

print version information

```text
usage: aeon version [-h] [--json]
```

| Opção | Padrão | Descrição |
|---|---|---|
| `--json` |  | print JSON |
