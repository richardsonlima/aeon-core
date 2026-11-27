# Modo shadow, e o que posso e não posso dizer sobre ele

!!! note "Rascunho para revisão"
    Não publicado. Escrito por Richardson Lima.

Eu gostaria de escrever "eis o que o modo shadow achou em produção". Não posso. **Ainda não há dados de campo.** Ninguém, eu incluído, rodou o Æon em shadow num agente de produção e relatou o que aconteceu. O que tenho é um método, um mecanismo e uma simulação. Este post é sobre o método, e sobre deixar claro em qual dos três cada afirmação se apoia.

## O método

1. **Envolva e registre.** Envolva o executor com `enforce`, mantenha `mode = "shadow"`, mantenha a auditoria ligada. Nada é impedido. A única coisa que muda é que toda decisão e seus motivos são gravados num log encadeado por hash.
2. **Leia o log antes de confiar numa regra.** `aeon audit tail --type decision`, ou exporte para CSV. Para cada veredito em `BLOCK`, pergunte se parar teria sido o certo.
3. **Conte os errados.** A taxa de falso positivo de uma regra no seu próprio tráfego é o número que decide se ela pode algum dia ser `BLOCK`.
4. **Observe o orçamento separadamente.** O orçamento de comportamento precisa de um período de baseline e os padrões não estão ajustados para o seu agente. Olhe `accumulated` e `max_accumulated` de cada agente em tráfego limpo, e defina limiares acima do que o tráfego limpo produz.
5. **Promova uma regra por vez.** `ALERT`, depois `LIMIT` (com um caminho de aprovação), depois `BLOCK` para regras que você sabe explicar.
6. **Ensaie a saída.** Saiba como liberar o Safe State e como acionar o kill-switch antes de precisar.

## No que se apoia

- **Mecanismo (sólido):** em modo shadow o gate registra o veredito e deixa a ação rodar. Testes cobrem que o shadow nunca aplica, exceto o kill-switch.
- **Simulação (sugestiva):** na minha campanha shadow com o agente roteirizado, 385 ações destrutivas sem aprovação rodaram em 30 execuções com falha enquanto o gate registrava um `BLOCK` para cada uma, e 1 de 30 execuções de controle limpas levantou um `BLOCK`. Isso me diz que o shadow mede exposição. Não me diz o que um agente real faria.
- **Evidência de campo (nenhuma):** não tenho um caso em que o modo shadow pegou um incidente real, nem um time real que moveu uma regra de shadow para enforce.

## O que contaria como evidência

Se você tentar, o relato útil é pequeno: quantas decisões por dia, quantos vereditos por nível, quantos dos `BLOCK` você julgou errados, se `audit.gap` apareceu, e quanto tempo a calibração levou. Um número assim de um agente real, inclusive um ruim, vale mais que tudo que medi num simulado. Vou publicar o que me enviarem, resultados desfavoráveis incluídos.

Veja também: [Adoção shadow-first](../concepts/shadow-first.md), [Implantar em modo shadow](../guides/shadow-rollout.md).
