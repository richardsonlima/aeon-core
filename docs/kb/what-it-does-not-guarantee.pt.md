# O que não garante

- **Cobertura.** Só ações que passam pelo executor envolvido são controladas. Um segundo caminho de código que chama a ferramenta direto, uma ferramenta que o agente alcança por outra biblioteca, ou um agente que nunca consulta o runtime é invisível ao gate.
- **Significado.** Axiomas veem nomes de ferramenta e valores de argumento. Não sabem se uma string é uma mentira, um vazamento ou uma injeção de prompt escrita diferente do seu padrão. Um modelo que responde com texto nocivo e não chama ferramenta não é impedido.
- **Completude do log.** A fila de auditoria é limitada. Num teste de rajada, 2.081 de 50.000 eventos foram descartados (registrados como `audit.gap`). A 1.000 eventos/s nenhum foi. Um processo que morre perde o que ainda está na fila.
- **Integridade contra quem escreve.** A cadeia detecta edição, remoção no meio, reordenação e linha corrompida. Remover registros do fim só é detectado com `--expect-head`. Quem tem acesso de escrita ao arquivo pode reconstruir a cadeia inteira; ainda não há assinatura nem âncora externa (roteiro).
- **Calibração sem dados.** Um orçamento precisa de um período de baseline. Antes de `baseline_n` resultados o score de desvio é 0.
- **Estatística sobre LLMs.** O comportamento de LLMs é não determinístico, então qualquer métrica sobre ele é estatística. As campanhas aqui usam um agente simulado com roteiro, não um LLM, então nem as taxas de detecção se transferem para um modelo real.
- **Poucos falsos positivos.** O orçamento padrão gerou falsos positivos em até 70% das execuções de controle limpas do agente simulado.
- **Um safety case.** Injeção de caos encontra problemas. Não é evidência de que um sistema é seguro, e o Æon não tem certificação.
- **Ações passadas.** Safe State e `BLOCK` param a próxima ação. Não desfazem a anterior.
- **Vários escritores.** Um processo escritor de auditoria por arquivo de log.

A lista completa, com a evidência de cada item, está em [Limites conhecidos](../known-limits.md).
