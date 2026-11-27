# Segurança

Esta página é o modelo de ameaças do próprio Æon: o que ele protege, de quem, e o que você precisa fazer se rodar o runtime além do seu notebook. Para reportar uma vulnerabilidade, veja o [`SECURITY.md`](https://github.com/richardsonlima/aeon-core/blob/main/SECURITY.md): só advisories privados, sem issues públicas.

## Ativos

| Ativo | Por que importa |
|---|---|
| As decisões e o modo do gate | Se um atacante puder mudá-los, o gate deixa de proteger. |
| Arquivos de axiomas e `aeon.toml` | Arquivos de axiomas são **código Python que o Æon importa e executa**. Quem pode escrevê-los pode executar código como o usuário do seu agente. |
| O log de auditoria | O registro do que o agente fez e do que o gate decidiu. |
| O token do runtime | Uma credencial de **operador** da API HTTP, que pode trocar o modo, acionar o kill-switch, alterar políticas, liberar Safe State e rodar campanhas. |
| O que o agente pode fazer | O alvo real: as ferramentas atrás do gate. |

## Fronteiras de confiança

- **Agente e gate compartilham um processo** quando você usa a biblioteca. O Æon não é um sandbox: código rodando no mesmo processo pode contornar ou alterar o gate. É um guard rail para as chamadas de ferramenta de um agente, não isolamento contra código hostil.
- **Cliente e runtime** conversam por HTTP no loopback por padrão, com um token bearer.
- **Runtime e sistema de arquivos**: o log de auditoria, o arquivo do token e os resultados de campanha são arquivos comuns com as permissões do seu usuário.
- **Saída de modelo e saída de ferramenta são entrada não confiável** para o agente. É o caso que o catálogo de falhas simula (saída envenenada, instruções conflitantes).

## Capacidades de atacante consideradas

| Atacante | O que o Æon faz | O que não faz |
|---|---|---|
| Injeta instruções pela saída de ferramenta | Os axiomas julgam a **ação** resultante, não o texto. Uma chamada de ferramenta negada é bloqueada em modo enforce. | Não lê nem higieniza o texto, e não impede uma ação a que nenhum axioma objeta. |
| Outro processo ou usuário na mesma máquina | O arquivo do token é criado com modo `0600`; a API exige o token. | Não defende contra root, nem contra um usuário que lê seus arquivos. |
| Página web no seu navegador (DNS rebinding) | Num bind em loopback o runtime aceita só os Host `localhost`, `127.0.0.1` e `[::1]` e rejeita outros com "Invalid host header". `AEON_RUNTIME_ALLOWED_HOSTS` (separados por vírgula) define a lista explicitamente e também vale em bind fora do loopback e em contêineres. | Num bind fora do loopback **sem** essa variável não há checagem de Host. Defina-a, ou deixe seu proxy impor. |
| Atacante de rede | O bind padrão é loopback e o runtime se recusa a escutar em outro lugar a menos que `AEON_RUNTIME_ALLOW_REMOTE=1`. | **Não há TLS**. Sem proxy, o token e os dados trafegam em texto claro. |
| Requisições grandes ou malformadas | Corpos acima de 1 MiB recebem 413. Limites da API de campanhas: `runs` e `controls` no máximo 1.000 cada, `steps` no máximo 1.000, `(runs + controls) * steps` no máximo 50.000, e parâmetros `*_ms` injetados entre 0 e 5.000. Alvos de campanha são nomes, nunca caminhos de arquivo. No máximo 16 clientes do stream de decisões (SSE). Decisões em buffer guardam argumentos serializados só até 16 KiB. O stdio do MCP rejeita linhas acima de 4 MiB e sobrevive a JSON muito aninhado. | Não há limitação de taxa de requisições. |
| Quem pode escrever o arquivo de auditoria | Edições, remoções no meio e reordenação são detectadas por `aeon audit verify`. Remoção do fim é detectada com `--expect-head`. | Pode reconstruir a cadeia inteira. Ainda não há assinatura nem âncora. |

## O que o token protege

Toda rota `/v1` exige `Authorization: Bearer <token>` e é comparada em tempo constante. `/health` e `/version` são abertas e não devolvem nada sensível. O token vem de `AEON_RUNTIME_TOKEN` ou de `.aeon/runtime.token`, criado no primeiro início com 32 bytes aleatórios e modo `0600` (um arquivo existente é ajustado para `0600`, e um link simbólico é recusado). Toda resposta traz `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` e uma Content-Security-Policy com `frame-ancestors 'none'`. O servidor imprime onde está o token, nunca o token. O stream de decisões (`/v1/decisions/stream`) também aceita `?token=` porque o `EventSource` do navegador não consegue definir cabeçalhos, então evite colocar essa URL em logs. A UI do painel guarda o token no fragmento da URL, que não é enviado ao servidor.

O token é uma **credencial de operador** ([ADR 003](decisions/003-operator-token-and-axiom-trust.md)). Ele autoriza tudo o que a API faz: **não há papéis**. Quem o tem pode trocar o modo para shadow, alterar políticas, liberar um Safe State ou soltar o kill-switch. **Nunca entregue o token a um agente.** Um agente com o token pode colocar o próprio gate em shadow. Um processo de agente que precisa de decisões deve usar a biblioteca (`enforce`) no próprio processo. Um token separado só para decisões está no roteiro, não construído.

## Arquivos de axiomas são código confiável

Arquivos de axiomas citados no `aeon.toml` são importados como Python. Iniciar `aeon runtime start` ou `aeon runtime mcp` num checkout em que você não confia executa o código desse checkout, como rodar o Makefile dele. Os dois comandos imprimem o caminho resolvido de cada arquivo de axiomas ao iniciar, para você ver o que foi carregado. A descoberta de configuração sobe a partir do diretório atual, e ainda não há aviso de confiança para ela (roteiro, não construído). Rode o Æon só em diretórios em que confia, ou passe `--config` explicitamente.

## Checklist para uso remoto

Não exponha o runtime a uma rede até marcar todas as caixas.

- [ ] Um proxy reverso termina o **TLS** na frente dele (o runtime não tem).
- [ ] `AEON_RUNTIME_ALLOWED_HOSTS` lista os nomes de host que os clientes usam (o `compose.yaml` define `localhost,127.0.0.1`), e o proxy limita quem conecta; acrescente limitação de taxa nele.
- [ ] `AEON_RUNTIME_ALLOW_REMOTE=1` é definido de propósito, e `AEON_RUNTIME_TOKEN` é um valor longo e aleatório vindo de um cofre de segredos, não um arquivo no repositório.
- [ ] Você tem um plano para **rotacionar o token**: mude `AEON_RUNTIME_TOKEN` (ou apague `.aeon/runtime.token`) e reinicie. Não há lista de revogação.
- [ ] O contêiner roda somente leitura com apenas o volume `/data` gravável, como usuário sem privilégios, com capabilities removidas (o `compose.yaml` faz isso) e a porta publicada em loopback ou numa rede interna.
- [ ] O arquivo de auditoria tem permissões restritas (o Æon o cria com `0600`; mantenha do usuário do runtime), fica num armazenamento que o agente não escreve, e o hash de cabeça é copiado para outro lugar periodicamente.
- [ ] Só um processo escreve cada arquivo de auditoria.
- [ ] `include_args` é `false`, a menos que você aceite argumentos brutos, que podem conter segredos, no log.
- [ ] Arquivos de axiomas e `aeon.toml` são graváveis só por quem faz deploy, porque são código.
- [ ] O token fica só com operadores, nunca com um processo de agente.

## Privacidade e telemetria

O Æon **não envia telemetria**. Nada sai da máquina a menos que o seu próprio código envie. `AEON_TELEMETRY` é ignorada. Por padrão o log de auditoria guarda o nome da ferramenta, os nomes dos argumentos e um sha256 dos argumentos (argumentos de baixa entropia podem ser adivinhados pelo hash). O site de documentação usa fontes do sistema e não carrega nada de terceiros; o pacote Python nunca contata nenhum servidor.

## MCP

`aeon runtime mcp` e `aeon docs mcp` usam stdio e rodam com os privilégios do processo que os inicia. `aeon_run_campaign` grava resultados em `.aeon/campaigns/`. O servidor de docs só lê arquivos `.md` dentro do seu diretório de docs e rejeita `..`, caminhos absolutos e links simbólicos que escapam.

## Não coberto

Sem verificação formal, sem teste de intrusão, sem auditoria de terceiros. A imagem de contêiner é construída localmente a partir do repositório, e nenhuma imagem é publicada. O pipeline de release prevê SBOM e proveniência de build, mas nada foi lançado ainda. Veja [Limites conhecidos](known-limits.md).
