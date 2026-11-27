# Runtime, painel de controle e Docker

O runtime é um pequeno serviço FastAPI em volta de um gate, para agentes que não são Python ou que vivem em outro processo. Ele **nunca executa uma ferramenta**: quem chama pergunta se uma ação pode rodar, e age sobre a resposta por conta própria.

## Instalar e iniciar

```bash
pip install "aeon-core[runtime]"
aeon runtime start                    # alias: aeon serve
```

```text
aeon runtime listening on http://127.0.0.1:8787
mode shadow; bearer token in /caminho/do/projeto/.aeon/runtime.token
```

Padrões: host `127.0.0.1`, porta 8787. O token vem de `AEON_RUNTIME_TOKEN` se definido, senão de `.aeon/runtime.token` (criado com modo `0600` no primeiro início). O runtime se recusa a iniciar em endereço fora do loopback a menos que `AEON_RUNTIME_ALLOW_REMOTE=1`. Leia [Segurança](../security.md) antes de mudar isso. O token é uma credencial de operador: nunca o entregue a um agente. Ao iniciar, o runtime também imprime o caminho de cada arquivo de axiomas que carrega, porque esses arquivos são Python confiável.

## Pedir uma decisão

```bash
TOKEN=$(cat .aeon/runtime.token)
curl -s -X POST localhost:8787/v1/actions/evaluate \
  -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"tool":"delete_file","args":{"path":"prod.db"},"agent":"demo"}'
```

```json
{"agent":"demo","tool":"delete_file","verdict":"BLOCK","mode":"shadow","allowed":true,"enforced":false,"safe_state":false,"findings":[{"axiom":"no_destructive_tool_call","level":"BLOCK","reason":"Destructive tools need explicit approval."}], "...": "..."}
```

Em shadow o veredito é `BLOCK` e `allowed` continua `true`. Seu agente roda a ferramenta e depois informa como foi com `POST /v1/actions/result`, para a baseline ver. Em enforce o seu cliente precisa respeitar `allowed: false`. A lista completa está na [referência da API HTTP](../reference/http-api.md).

## MCP

`aeon runtime mcp` serve o gate por MCP em stdio, com as ferramentas `aeon_check_action`, `aeon_status`, `aeon_audit_verify` e `aeon_run_campaign` ([referência](../reference/mcp.md)). `aeon docs mcp` serve esta documentação a um agente de código.

## Painel de controle (UI)

```bash
aeon ui          # inicia o runtime e abre o navegador nele
aeon ui --no-browser
```

A UI são arquivos estáticos servidos pelo runtime em `/ui/`, e tem telas de visão geral, decisões, campanhas, log de auditoria e alegações, tudo pela mesma API. O token viaja no fragmento da URL (`#token=...`), que os navegadores não enviam ao servidor.

## Docker

O repositório tem um `Dockerfile` e um `compose.yaml`. Nada é publicado: nenhuma imagem é enviada a lugar algum. Construa localmente:

```bash
python -c "import secrets;print('AEON_RUNTIME_TOKEN=' + secrets.token_urlsafe(32))" > aeon.env
docker compose up --build
```

O contêiner roda como usuário sem privilégios, escuta em `0.0.0.0` por dentro (por isso a imagem define `AEON_RUNTIME_ALLOW_REMOTE=1`), e o `compose.yaml` publica a porta só em `127.0.0.1`, com sistema de arquivos raiz somente leitura, todas as capabilities removidas e `no-new-privileges`. Os dados ficam no volume `/data`. Não faça commit do `aeon.env`.

Não executei o build do contêiner no ambiente em que escrevi esta página (sem Docker lá), então trate o compose como revisado, não exercitado.

## Limites

A página de decisões, o stream e os contadores só enxergam decisões feitas por este processo do runtime; decisões feitas em outro lugar aparecem só no log de auditoria. Um gate por processo, um escritor de auditoria por arquivo de log, sem backend Postgres. Uma campanha iniciada por HTTP roda em uma thread de trabalho, uma por vez. Veja [Limites conhecidos](../known-limits.md).
