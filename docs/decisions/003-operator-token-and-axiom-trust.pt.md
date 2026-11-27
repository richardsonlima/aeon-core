# 003. Um token de operador; arquivos de axiomas são código confiável

- Status: aceita
- Data: 2026-11-27

Esta página é um resumo em português. O texto de referência, em inglês, é [003-operator-token-and-axiom-trust.md](003-operator-token-and-axiom-trust.md).

**Contexto.** Uma revisão de segurança do runtime achou dois pontos de projeto. O token bearer único serve tanto para pedir decisões quanto para alterar o gate (`/v1/mode`, `/v1/kill-switch`, `/v1/policies`, reset de Safe State), então um agente com o token poderia colocar o próprio gate em shadow. E os arquivos de axiomas listados no `aeon.toml` são importados como Python, então iniciar o runtime ou o servidor MCP num checkout não confiável executa o código desse checkout.

**Decisão.** O token é uma credencial de **operador**: agentes não devem recebê-lo; um processo de agente que precisa de decisões deve usar a biblioteca (`enforce`) no próprio processo. `aeon runtime start` e `aeon runtime mcp` imprimem o caminho resolvido de cada arquivo de axiomas ao iniciar. Um token separado só para decisões e um aviso de confiança para configurações descobertas subindo a partir do diretório atual estão no roteiro, não implementados.

**Consequências.** A instalação simples continua simples. O risco é documentado, não removido, e está em [Limites conhecidos](../known-limits.md).
