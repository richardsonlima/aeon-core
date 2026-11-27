# Implantar em modo shadow

Uma sequência concreta para colocar o gate na frente de um agente real sem impedir nada no primeiro dia. O raciocínio está em [Adoção shadow-first](../concepts/shadow-first.md).

## Dia 1: shadow, auditoria ligada

```bash
aeon init                    # grava aeon.toml (mode = "shadow") e aeon_axioms.py
aeon doctor
```

Envolva o executor com `enforce` (veja [Python simples](plain-python.md) ou um adaptador) e publique. Nada é impedido. Toda decisão vai para `.aeon/audit.jsonl`. Se você não pode gravar em disco local, use `audit = "memory"` ou um caminho `sqlite:`, e lembre que "off" significa nenhum registro.

## Primeira semana: leia o log

```bash
aeon audit tail -n 200 --type decision
aeon audit export --format csv -o decisions.csv
aeon audit verify
```

Perguntas a responder com tráfego real:

1. Quais axiomas disparam, com que frequência, em quais ferramentas?
2. Nos vereditos `BLOCK`, parar teria sido o certo? Conte os errados.
3. Como é a baseline? `GET /v1/status` (ou `aeon_status` por MCP) mostra o progresso de calibração, `deviation`, `accumulated` e o nível de cada agente.
4. Aparece `audit.gap`? Então a sua taxa de eventos excede a fila.

## Depois: promova uma regra por vez

1. Defina os limiares do orçamento a partir do que viu ([Como calibrar um orçamento](../kb/calibrate-budget.md)). Mantenha em `ALERT` primeiro.
2. Passe as regras em que confia para `LIMIT` e ligue um caminho de aprovação.
3. Passe para `enforce` com um agente, com uma regra `BLOCK` que você saiba explicar. Mantenha as outras em shadow. O modo vale para o gate inteiro, então use um gate ou deploy separado se precisar de modos por agente.
4. Ensaie a saída: `gate.reset("agent")` e o kill-switch, para o primeiro Safe State não ser a primeira vez que alguém os usa.

## Voltando atrás

Defina `mode = "shadow"` (ou `AEON_MODE=shadow`, ou `POST /v1/mode`). A mudança fica registrada no log de auditoria como um evento `mode`.

## Antes de confiar num veredito

Rode uma [campanha](campaigns.md) com uma falha que importa para você, em `staging`. E leia [O que o BLOCK garante](../kb/what-block-guarantees.md) e [Limites conhecidos](../known-limits.md).
