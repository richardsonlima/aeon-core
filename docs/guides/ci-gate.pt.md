# Gate de resiliência no CI

`aeon chaos run ... --strict` sai com 1 quando a hipótese de uma campanha não é suportada. Isso transforma uma campanha num check de CI: "com esta falha injetada, o gate ainda pega e nenhuma ação nociva roda".

```yaml
# .github/workflows/resilience.yml
name: Resilience
on: [pull_request]
jobs:
  chaos:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      # Até a primeira versão no PyPI, instale do git; depois: pip install aeon-core
      - run: pip install "aeon-core @ git+https://github.com/richardsonlima/aeon-core@main"
      - run: aeon doctor
      - run: aeon chaos run campaigns/our-poisoned-output.toml --strict
      - if: always()
        run: aeon report our-poisoned-output -o chaos-report
      - if: always()
        uses: actions/upload-artifact@v4
        with: { name: chaos-report, path: chaos-report.* }
```

## Leia isto antes de adicionar

- **As campanhas do repositório não passam em `--strict`.** Na execução versionada, sete das oito campanhas tiveram a hipótese não suportada, principalmente porque o orçamento padrão gera falsos positivos no tráfego limpo do agente simulado ([números](../evidence/benchmarks.md)). Não aponte o CI para elas como estão. Escreva sua própria campanha com limiares que você alcançou em execuções suas, e defina `max_false_positive_rate` com honestidade.
- **Códigos de saída.** `0` suportada, `1` não suportada (só com `--strict`), `2` erro de uso, como falha desconhecida ou raio de impacto acima do teto.
- **Determinismo.** As sementes são fixas, mas o agente simulado dorme alguns milissegundos por chamada e as falhas adicionam atrasos, então resultados baseados em latência variam entre execuções. Deixe margem entre o limiar e o que você mediu, e use execuções suficientes (30 é o tamanho das campanhas do repositório, e o intervalo de 95% é largo).
- **Custo.** Cada campanha do repositório levou cerca de 7 a 9 segundos na máquina de referência, com 30 execuções com falha e 30 controles.
- **Escopo.** A campanha exercita o gate e seus axiomas contra um agente simulado. Não testa seu agente ou modelo reais. Veja [Limites conhecidos](../known-limits.md).

## Um gate em que dá para confiar

Fixe o arquivo da campanha no repositório, altere-o só em commit revisado, e mantenha os resultados desfavoráveis no relatório. Um limiar que é subido em silêncio até o CI ficar verde não é evidência.
