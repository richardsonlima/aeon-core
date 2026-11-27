# O que o BLOCK garante

Com precisão, e nada além. Cada linha é sustentada por um teste listado em [Alegações](../claims.md).

Em modo **enforce**, para uma ação que passa por um executor protegido (`enforce(...)`, um `ToolBox`, `guard_tools`, ou a chamada evaluate do runtime respeitada pelo seu cliente):

1. **A decisão vem primeiro.** O gate decide antes de o executor rodar. Um veredito `BLOCK` significa que o executor não é chamado e `ActionBlocked` é levantada (`gate-before-execution`).
2. **O agente fica retido.** Depois de um `BLOCK`, toda ação seguinte desse agente é bloqueada com `SafeStateActive` até `gate.reset(agent)` (`safe-state`).
3. **A falha é fechada.** Se um axioma levantar exceção, ou o próprio gate falhar, a ação é bloqueada (`fail-closed`).
4. **Um `LIMIT` sem aprovação não roda.** Levanta `ActionLimited`, a menos que a ação esteja aprovada ou o gancho de aprovação diga sim. Um gancho que levanta exceção não aprova.
5. **O kill-switch para tudo.** Toda ação de todo agente, em qualquer modo (`kill-switch`).
6. **A decisão é registrada** com o melhor esforço: o evento vai para uma fila limitada e é escrito por uma thread de fundo (veja abaixo), e a cadeia permite detectar adulteração depois.

Em modo **shadow**, nenhum dos itens 1 a 4 vale: o veredito é registrado e a ação roda. Só o kill-switch é aplicado.

## Nas campanhas versionadas

Em modo enforce, nas sete campanhas enforce (30 execuções com falha cada), o número de ações destrutivas sem aprovação executadas foi 0. É uma medição num agente simulado que segue instruções injetadas com probabilidade 0,7, e cujas únicas ferramentas destrutivas são `delete_files` e `send_email`. Não é uma prova.

## O que ainda não dá

Veja [O que não garante](what-it-does-not-guarantee.md). A lista curta: caminhos que contornam o gate, texto livre, eventos de auditoria descartados, uma cadeia reconstruída, e qualquer coisa que aconteceu antes de o gate estar na frente da ferramenta.
