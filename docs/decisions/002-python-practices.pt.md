# 002. Práticas de desenvolvimento Python

- Status: aceita
- Data: 2026-11-27

Esta página é um resumo em português. O texto de referência, em inglês, é [002-python-practices.md](002-python-practices.md).

Em resumo: layout `src`, lockfile `uv.lock` versionado, ferramentas de desenvolvimento e de documentação em `[dependency-groups]`, ruff com conjunto de regras escolhido e docstrings no estilo Google, mypy em modo estrito, piso de cobertura, varredura de dependências e de segredos no CI, bibliotecas que só criam loggers, e nenhum `except` silencioso. Os desvios mantidos de propósito (Python 3.10+ e núcleo sem dependências de terceiros) estão no texto em inglês.
