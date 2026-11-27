# Prompt para um agente de código

Se um agente de código (qualquer um que rode comandos de shell) vai ligar o Æon ao seu projeto, entregue a ele o prompt abaixo. Ele usa só comandos documentados e mantém o agente em modo shadow até você decidir o contrário.

```text
Você vai adicionar o Æon (aeon-core) a este projeto Python para proteger as ações de um agente LLM.
Trabalhe em passos pequenos e me mostre a saída de cada comando.

Regras:
- Não mude o modo para "enforce" e não remova "mode = shadow". Eu decido quando aplicar.
- Não edite nem apague nada em .aeon/ à mão. Nunca coloque segredos em axiomas ou configuração.
- Use só estes comandos: aeon version, aeon doctor, aeon init, aeon axioms list,
  aeon axioms check <arquivo>, aeon run <script> [--mode shadow|enforce], aeon audit tail,
  aeon audit verify, aeon chaos list, aeon chaos run <falha-ou-campanha>, aeon report.

Passos:
1. Rode `aeon version` e `aeon doctor`. Se o aeon não existir, pare e me avise.
2. Ache a função única pela qual o agente executa ferramentas. Se houver várias,
   liste e me pergunte.
3. Rode `aeon init` na raiz do projeto. Ele grava aeon.toml (modo shadow) e aeon_axioms.py.
4. Edite aeon_axioms.py para os axiomas refletirem as ferramentas que este agente realmente tem:
   ferramentas destrutivas precisam de `action.approved`. Use @axiom(on_violation="BLOCK") ou os
   auxiliares de aeon.axioms.builtin. Depois rode `aeon axioms check aeon_axioms.py`.
5. Envolva o executor com `aeon.axioms.enforce` (decorador ou `enforce(fn)`). Dê ao agente um
   nome estável com enforce(..., agent="<nome>").
6. Rode o agente uma vez com `aeon run <script>` (modo shadow). Depois rode `aeon audit tail` e
   `aeon audit verify` e resuma quais axiomas dispararam e o que teriam bloqueado.
7. Rode `aeon chaos run "poisoned output" --runs 10 --controls 10` e cole o resultado,
   incluindo falsos positivos. Não esconda um resultado desfavorável.
8. Relate: arquivos alterados, comandos executados, o resumo da auditoria, e o que o gate não
   cobre (ações que contornam o executor envolvido, e o significado de texto livre).

Documentação deste projeto: rode `aeon docs mcp` para lê-la por MCP, ou veja
https://www.richardsonlima.com.br/aeon/docs/ e o llms.txt de lá.
```

## Dê a documentação ao agente

`aeon docs mcp` serve estas páginas a um agente de código por MCP (stdio), com `search_docs` e `read_doc`, e cada página como recurso `aeon-docs://<caminho>`. Adicione como servidor MCP na configuração do seu agente:

```json
{ "mcpServers": { "aeon-docs": { "command": "aeon", "args": ["docs", "mcp"] } } }
```

Ele lê o diretório `docs/` de um checkout do código-fonte, ou a cópia embutida no pacote. O site também publica o [llms.txt](https://www.richardsonlima.com.br/aeon/docs/llms.txt).
