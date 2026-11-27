# Adoção shadow-first

Adote em quatro passos. Cada um é reversível, e você só avança quando o log de auditoria dá motivo.

| Passo | Modo e nível | O que fazer | Avance quando |
|---|---|---|---|
| 1. Shadow | `mode = "shadow"` | Envolva os executores com `enforce`. Nada é impedido; toda decisão e veredito é registrado. | Você leu tráfego real com `aeon audit tail` e sabe quais axiomas disparam, e com que frequência. |
| 2. `ALERT` | shadow ou enforce, regras em `ALERT` | As regras registram e nunca interferem. Ajuste até os alertas valerem a leitura. | A taxa de alertas é baixa o bastante para uma pessoa olhar cada um. |
| 3. `LIMIT` | `enforce`, regras em `LIMIT` | Ações arriscadas exigem aprovação. Ligue um aprovador ou `Action.approved`. | As aprovações são raras e quem aprova dá conta. |
| 4. `BLOCK` | `enforce`, poucas regras em `BLOCK` | Só regras em que você confia e que sabe explicar: ferramentas destrutivas, padrões de exfiltração. | Você aceita que um agente bloqueado entra em [Safe State](safe-state.md) até alguém liberar. |

Instalações novas começam em modo shadow, e `aeon init` escreve `mode = "shadow"`.

## Por que nessa ordem

Um axioma é código que você escreveu sobre o que é seguro. Na primeira vez que encontrar tráfego real, ele vai estar errado em algum ponto. Em shadow, uma regra errada custa uma linha de log. Em `BLOCK`, ela para um agente. O [orçamento](budget.md) é pior: os padrões deram taxas de falso positivo de até 73% no agente simulado (veja o [post](../blog/first-unfavourable-result.md)), então rode em `ALERT` primeiro e calibre.

O shadow também mostra o que você teria pego. Na campanha shadow versionada, 385 ações destrutivas sem aprovação rodaram em 30 execuções com falha enquanto o gate registrava um `BLOCK` para cada uma. É o número que o shadow evita que você chute.

## O que o shadow não protege

Em shadow nada é impedido, por projeto, exceto pelo kill-switch. Se você precisa de proteção desde o primeiro dia, shadow não é isso. Comece com uma lista pequena de `deny_tools` em `BLOCK` para as ferramentas que você nunca quer sem revisão, e mantenha o resto em shadow.

Guia: [Implantar em modo shadow](../guides/shadow-rollout.md). KB: [Por que shadow primeiro](../kb/why-shadow-first.md).
