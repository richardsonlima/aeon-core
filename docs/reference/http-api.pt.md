# Referência da API HTTP

!!! info "Página gerada"
    Esta página é gerada por `scripts/gen_reference.py` a partir de `create_app().openapi()`. Não edite à mão; altere a fonte e rode o script de novo.


O runtime local (`aeon runtime start`, alias `aeon serve`) serve esta API. Ele decide e registra; nunca executa uma ferramenta. Toda rota `/v1` exige `Authorization: Bearer <token>`. O documento legível por máquina é o [openapi.json](openapi.json). Um `?` depois do nome do campo significa opcional. As descrições abaixo vêm do código e estão em inglês.

| Método | Caminho | O que faz | Autenticação | Corpo da requisição |
|---|---|---|---|---|
| GET | `/health` | Liveness. Always `{"status": "ok"}`. | none |  |
| GET | `/version` | Runtime version. | none |  |
| POST | `/v1/actions/evaluate` | Ask the gate to decide an action. Returns the decision record. The action is not executed. | Bearer | `tool`: string, `args`?: object, `agent`?: string, `approved`?: boolean, `context`?: object |
| POST | `/v1/actions/result` | Report the outcome of an action that ran (latency, ok, tokens, cost) so the baseline and the audit log see it. | Bearer | `action_id`?: string/null, `tool`: string, `agent`?: string, `latency_ms`: number, `ok`?: boolean, `tokens`?: integer/null, `cost`?: number/null |
| GET | `/v1/status` | Mode, axioms, kill-switch, Safe States, counters, budget and audit health. | Bearer |  |
| GET | `/v1/policies` | List axioms and whether each is enabled. | Bearer |  |
| PUT | `/v1/policies/{name}` | Enable or disable one axiom. | Bearer | `level`?: string/null, `enabled`?: boolean/null |
| POST | `/v1/mode` | Switch between `shadow` and `enforce`. | Bearer | `mode`: string |
| POST | `/v1/kill-switch` | Engage or release the kill-switch. | Bearer | `engaged`: boolean, `reason`?: string/null |
| POST | `/v1/safe-state/{agent}/reset` | Release an agent from Safe State. | Bearer |  |
| GET | `/v1/decisions` | Recent decisions from the in-memory ring buffer, newest first. | Bearer |  |
| GET | `/v1/decisions/stream` | Server-sent events: every new decision as it happens. | Bearer, or `?token=` (EventSource cannot set headers) |  |
| GET | `/v1/campaigns` | List campaign jobs and saved results. | Bearer |  |
| POST | `/v1/campaigns` | Start a chaos campaign in the background (one at a time). | Bearer | `target`?: string/null, `campaign`?: object/null, `runs`?: integer/null, `controls`?: integer/null, `seed`?: integer/null, `blast_radius`?: string/null |
| GET | `/v1/campaigns/{campaign_id}` | Status or result of one campaign. | Bearer |  |
| GET | `/v1/audit` | Tail the audit log. | Bearer |  |
| POST | `/v1/audit/verify` | Recompute the hash chain; optionally check the expected head. | Bearer | `expect_head`?: string/null |
| GET | `/v1/audit/export` | Export the audit log as JSONL or CSV. | Bearer |  |
| GET | `/v1/claims` | The claims document (`docs/claims.json`), when present. | Bearer |  |
