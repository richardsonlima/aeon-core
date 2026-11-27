# 001. Reescrever o pacote para a v0.5.0

- Status: aceita
- Data: 2026-11-27

## Contexto

A v0.4.0 é um framework de assistente geral com 17 dependências obrigatórias, sem testes e sem script de console. O escopo da v0.5.0 define outro produto: um gate de ações pequeno e sem dependências, com injeção de caos e um log de auditoria encadeado por hash.

## Decisão

Substituir o conteúdo de `src/aeon/` pelo desenho da v0.5.0. Remover os documentos e pastas de exemplo legados. O código legado permanece na tag `v0.4.0-ULTRA`.

## Consequências

- Quem usa `aeon.Agent` e os subpacotes da v0.4 deve fixar `aeon-core==0.4.0`. Isso está dito no `CHANGELOG.md`, em "Removed".
- A instalação do núcleo não tem dependências de terceiros. FastAPI, uvicorn e SDKs de provedores viram extras.
