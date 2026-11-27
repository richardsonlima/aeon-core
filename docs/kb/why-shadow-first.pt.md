# Por que shadow primeiro

**Resposta curta:** uma regra que você não viu em tráfego real é um palpite, e em `BLOCK` um palpite errado para um agente que funciona.

## O que o modo shadow faz

Em modo `shadow` o gate roda todo axioma e o orçamento, registra o veredito e os motivos no log de auditoria, e deixa a ação rodar. A única exceção é o kill-switch, que vale em todos os modos. Instalações novas e `aeon init` começam em shadow.

## O que os números do próprio repositório dizem

- **Regras e orçamentos erram.** Com o orçamento padrão, as execuções de controle limpas do agente simulado dispararam alarme em 20% a 70% das execuções em seis das oito campanhas enforce (veja [Como ler um resultado desfavorável](unfavourable-result.md)). Se fossem `BLOCK`, o agente teria sido parado sem motivo. Em shadow são linhas de log.
- **O shadow mostra a exposição.** Na campanha shadow versionada, 385 ações destrutivas sem aprovação rodaram em 30 execuções com falha enquanto o gate registrava um `BLOCK` para cada uma, e a taxa de falso positivo nos controles foi 3,3% (1 de 30). Você descobre o que teria pego antes de deixá-lo agir.
- **Tem um custo que você deve conhecer.** O shadow não protege. Aquelas 385 ações rodaram. Se uma ferramenta nunca deve rodar sem revisão, ponha nela uma regra `BLOCK` pequena desde o primeiro dia e mantenha o resto em shadow.

## O que olhar enquanto está em shadow

1. Quais axiomas disparam, com que frequência, em quais ferramentas (`aeon audit tail --type decision`).
2. Para cada veredito `BLOCK`, parar teria sido o certo?
3. Como o orçamento se comporta: progresso de calibração, `accumulated` e `max_accumulated` por agente em `GET /v1/status` ou `aeon_status`.
4. Se aparecem registros `audit.gap` (sua taxa de eventos excede a fila) ou `audit.backend_error` (o armazenamento falhou).

## Quando avançar

Avance uma regra por vez, quando o log mostrar que os vereditos dela estavam certos e os falsos positivos estão num nível que você aceita. A ordem é `ALERT`, `LIMIT`, `BLOCK`. Veja [Adoção shadow-first](../concepts/shadow-first.md) e [Implantar em modo shadow](../guides/shadow-rollout.md).

## Ressalva

Ainda não há dados de campo. Ninguém, eu incluído, rodou o Æon em shadow num agente de produção e relatou resultados. O raciocínio aqui vem das campanhas simuladas e de como o gate funciona, não de experiência em produção. Veja o [post sobre o método](../blog/shadow-mode-method.md).
