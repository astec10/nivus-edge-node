# Execução persistente de tarefas de desenvolvimento com IA

**Tema:** agentes de desenvolvimento, roteamento de modelos, fila de trabalho, CI e aprovação humana.  
**Fonte do caso:** descrição de um comentário enviada pelo operador e vídeo [Paralelismo com IAs, Multi Contas](https://www.youtube.com/watch?v=Q-yobCYc71A).  
**Estado da verificação do vídeo:** o YouTube não forneceu legenda/transcrição nesta revisão. O ciclo exato relatado pelo comentarista não está confirmado; os componentes abaixo foram verificados separadamente em documentação oficial.

## Método descrito

O relato descreve um executor sempre disponível numa VPS: Discord recebe a solicitação; Jira mantém estado e comentários; Hermes executa a tarefa; OmniRoute encaminha chamadas aos modelos/provedores configurados; o agente trabalha em ambiente separado e cria um pull request; CI valida e publica em homologação; uma pessoa revisa e faz o merge. Comentários que pedem correção voltam a uma fila de trabalho.

Isso é um padrão de orquestração, não instalação pronta nem execução literalmente “sem parada”. O processo continua enquanto o host, a rede, as credenciais, os provedores e as quotas funcionam. Falhas ou aprovação pendente suspendem a tarefa.

## Componentes e fronteiras

- **Hermes:** agente/gateway de execução e interface de mensagens. A documentação do projeto explica gateway persistente em container, Discord e webhooks.
- **OmniRoute:** gateway/roteador compatível com interfaces de modelos, com seleção configurada de provedores. Ele não implementa sozinho estado de Jira, leases, worktrees ou aprovação de PR.
- **Discord/Jira:** entrada e acompanhamento de trabalho. Um webhook recebido não concede autorização para editar issues; a ponte precisa de ferramenta/API e OAuth com escopo mínimo.
- **GitHub Actions:** validação e deploy em homologação. Um reviewer humano pode ser exigido para promover deploy; merge para produção continua manual.
- **Executor:** controlador leve supervisionado por systemd e worker em sandbox efêmera, com limites e credenciais de curta duração. O controlador e o worker podem estar em máquinas diferentes.

## Ciclo robusto recomendado

```text
requested -> triaged -> queued -> leased -> running -> pull_request -> ci -> staging_review
                                             |                         |
                                             +-> retry (bounded)       +-> human merge
```

1. Aceitar apenas emissores/canais autorizados e validar assinatura, nonce e replay de webhooks.
2. Converter o pedido em critérios de aceite, limites, risco e orçamento antes de executar.
3. Reservar uma tarefa com lease/heartbeat; idempotência impede duas execuções concorrentes do mesmo item.
4. Selecionar modelo por regra explícita de custo, latência, especialidade e quota, registrando provedor e uso.
5. Executar em sandbox efêmera/worktree própria. Conteúdo de tickets, comentários, arquivos e resultados é entrada não confiável.
6. Limitar tempo, tentativas e consumo; persistir estado e artefatos para sobreviver a reinício. Encerrar em estado de erro quando exceder limites, sem loop infinito.
7. Criar PR, executar CI e publicar somente em homologação automática. Exigir revisão humana para merge/produção.
8. Tratar comentário de correção como uma nova tentativa vinculada ao PR, com histórico e novo limite de tentativas.

## O que o Nivus pode aproveitar

O desenvolvimento externo pode usar esse fluxo para preparar mudanças no repositório Nivus. Ele não é runtime do nó de borda. Para distribuição futura entre máquinas Nivus, a Fase 5 do roadmap exige identidade, capacidade anunciada, leases, quotas, cancelamento, isolamento, verificação de artefatos e recuperação de falhas. A Fase 4 da biblioteca pode fornecer conhecimento citável a esses workers.

## Projetos de referência avaliados para o Nivus

| Base | Padrão útil | Decisão |
|---|---|---|
| [GitHub Issues + GitHub Actions do próprio Nivus](https://github.com/astec10/nivus-edge-node/tree/main/.github/workflows) | Issue como fila durável; evento `ai:ready` inicia worker isolado e PR em rascunho. | Adotado. O notebook só acompanha e autoriza; o runner hospedado executa a tarefa. |
| [LeaseQueue](https://github.com/kyan9400/leasequeue) | Lease atômico, idempotência, retry limitado e dead-letter em serviço FastAPI/SQLite. | Referência para futuros workers Nivus. Não duplicamos a fila local: Issues já persiste as tarefas e Actions mantém a execução. |
| [simpleq](https://github.com/trtrojo/simpleq) | Exemplo pequeno de fila FastAPI/SQLite com workers que reivindicam e confirmam tarefas. | Não adotado nesta etapa porque criaria uma segunda fila e outra dashboard paralela. |
| [run-gemini-cli do Google](https://github.com/google-github-actions/run-gemini-cli) | Action para invocar Gemini CLI em workflows, com modos de triagem, análise e alteração. | Mantemos o worker Nivus existente, que valida caminhos exatos, aplica mudanças limitadas e abre PR em rascunho. A Action é apenas referência para análise sem escrita. |

Avaliados pelos READMEs e metadados dos repositórios públicos. Nenhum código desses projetos foi copiado nem adicionado como dependência. O Nivus reaproveita ideias de idempotência e confirmação e preserva Issues/Actions como fonte única da fila e execução.

## Execução contínua sem o PC do operador

GitHub Issues guarda a fila e GitHub Actions executa as tarefas em runners hospedados. Um controlador leve opcional na API do notebook acompanha essa fila continuamente e oferece revisão/autorizações na dashboard. O PC pessoal pode ficar desligado; o notebook precisa permanecer ligado e com saída HTTPS para GitHub para manter a tela e a consulta atualizadas. Se o notebook ficar offline, Issues e Actions continuam disponíveis e o intake do GitHub segue como alternativa.

```text
GitHub Issue validada (ai:queued)
  -> mantenedor revisa e autoriza (intake + ai:ready)
  -> GitHub Actions ubuntu-24.04 efêmero
  -> Gemini free-tier recebe somente contexto público/sintético
  -> proposta aplicada aos caminhos exatos e PR em rascunho
  -> CI e revisão humana

Notebook online: controlador/API de baixo consumo consulta Issues; a dashboard permite aprovar cada chamada individual.
```

O controlador fica desligado por padrão. O administrador configura o repositório, um token fine-grained e intervalo de consulta entre 30 e 900 segundos na **Configuração → Executor GitHub**; testa a conexão e então habilita o serviço. O token fica cifrado com a chave mestra que já é externa ao SQLite. Conceda somente `Issues: Read and write` para o repositório Nivus e `Metadata: read` (automático); o controlador não precisa de `Contents` nem `Actions` write.

A dashboard mostra Issues `ai:queued` e `ai:ready`, limita autorizações configuradas pelo administrador (1–10 por janela móvel de 24 horas; padrão 3) e nunca chama o modelo automaticamente. Cada botão exige confirmação da revisão da Issue e de uma única chamada free-tier; a confirmação não é um teto de cobrança, então o operador deve conferir faturamento e quota na conta do provedor. O Nivus valida novamente formulário, risco, classificação pública/sintética, tempo e allowlist antes de adicionar apenas `ai:ready`. O evento existente inicia o workflow GitHub; CI e geração de proposta rodam no runner hospedado. Merge e deploy continuam humanos.

A API não faz checkout, build ou execução de código da Issue. Seu container recebe uma rede Docker de saída para acessar `api.github.com` por HTTPS; não publica porta nova e não requer encaminhamento de portas na ONU. A integração fixa o host da API e valida/pina DNS público. A administração remota da dashboard deve usar VPN. Quedas de rede deixam a Issue no GitHub; a API volta a consultar no intervalo seguinte e confere o rótulo antes de repetir qualquer autorização. Se não conseguir confirmar o resultado de uma solicitação, a dashboard instrui atualizar o estado antes de tentar de novo.

O controlador facilita monitoramento e aprovação sem depender do PC, mas não é a fila nem o executor. Se o notebook ficar desligado, GitHub continua guardando e executando Issues já autorizadas; novas tarefas ainda podem ser submetidas pelo intake em **Actions → AI task intake**. Telemetria do Nivus não é dependência; agregação entre nós será útil quando o Nó Master estiver operacional.

O executor inicial foi integrado ao `main` no PR #3; o mantenedor confirmou a configuração de `GEMINI_API_KEY` e `NIVUS_AI_BUDGET_MODE=free-tier`, sem expor o valor da chave. Duas tentativas anteriores falharam (HTTP 503 e timeout síncrono); o adaptador foi então alterado para polling em segundo plano limitado, sem repetir chamadas POST, e testes simulados. Uma chamada autorizada para a Issue #6 gerou o documento proposto no PR #16, cuja CI passou. A etapa de criação automática do draft falhou porque `gh repo view` foi executado sem checkout, e o mantenedor abriu o draft manualmente. O commit `bec9573` corrigiu a workflow para obter o branch padrão via API sem checkout. O PR #53 adicionou verificação read-only para pular uma chamada quando há draft aberto da mesma issue; ao criar um PR, remove rótulos da fila e publica comentário com o link. Os checks hospedados passaram. Uma nova chamada autorizada numa issue separada ainda será necessária para verificar a abertura automática após a correção. O executor não aprova, mescla ou implanta.

Com os recursos informados para o CCE U25 (2 núcleos e cerca de 3,2 GiB de RAM), ele não é o local recomendado para manter agentes de código, builds paralelos ou sandboxes. Um runner padrão `ubuntu-24.04` hospedado pelo GitHub oferece 4 vCPU e 16 GB de RAM para repositórios públicos, com uso padrão gratuito segundo a documentação atual. Isso fornece computação, não créditos de modelo. O runner hospedado executa; o notebook pode ajudar a observar e agregar relatórios quando estiver online.

Não configure um runner self-hosted GitHub no CCE para executar código de PRs públicos. O GitHub alerta que workflows com código não confiável podem comprometer o host e acessar credenciais. “Offline” aqui significa que o operador pode estar ausente e os computadores locais desligados; o runner e a API continuam precisando de Internet. A quota gratuita do modelo pode pausar novas propostas, sem perder as Issues da fila.

## Paralelismo de módulos: construtores e integrador

Várias IAs podem construir peças ao mesmo tempo quando cada tarefa tiver caminho de arquivos próprio, contrato documentado, dependências e critérios de aceite. O integrador divide uma entrega em Issues relacionadas, marca a ordem das dependências e distribui cada peça para um branch/worktree isolado. Módulos que alterem contratos compartilhados (como schemas, banco, autorização, Compose ou tópicos MQTT) recebem primeiro um contrato escrito e um único responsável por integrá-lo. Cada peça passa CI; o integrador resolve compatibilidade e abre/atualiza o PR final para revisão humana. Sem essas fronteiras, o paralelismo cria conflitos e não garante qualidade.

O mapa de pacotes, dependências e critérios do modelo “cada agente constrói uma peça; o integrador monta” está em [`AI_MODULE_WORKPLAN.md`](AI_MODULE_WORKPLAN.md).

## Limites e segurança

- Não use várias contas para contornar limites, políticas ou termos do provedor; cada conta mantém suas próprias quotas e condições.
- Não dê root, acesso geral ao host, segredos pessoais ou permissão para editar regras de proteção ao agente.
- Não deixe o agente fazer merge ou deploy de produção. Proteja branches, exija CI e mantenha logs auditáveis.
- Chamadas em paralelo podem comparar respostas, mas não combinam a memória das GPUs numa máquina virtual de hardware maior.
- O diagrama é uma recomendação baseada nos componentes, não uma afirmação de que o vídeo demonstrou cada etapa.

## Fontes primárias dos componentes

- [Hermes: gateway Docker persistente](https://hermes-agent.nousresearch.com/docs/user-guide/docker)
- [Hermes: Discord e allowlist](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord)
- [Hermes: webhooks](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/webhooks/)
- [OmniRoute: agentes CLI, incluindo Hermes](https://github.com/cheaper-inference/OmniRoute/blob/main/docs/reference/CLI-TOOLS.md)
- [GitHub Actions: revisão de deploys](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/review-deployments)
- [GitHub Actions: capacidade e custo dos runners hospedados](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
- [GitHub Actions: uso seguro de runners](https://docs.github.com/en/actions/reference/security/secure-use)
- [Hermes: requisitos e limites de recursos do Docker](https://hermes-agent.nousresearch.com/docs/user-guide/docker/)


## Avaliação: run-gemini-cli do Google

**Verificado em 2026-11-15.** A Action [`google-github-actions/run-gemini-cli`](https://github.com/google-github-actions/run-gemini-cli) é uma integração do Google para executar o Gemini CLI em runners do GitHub Actions. O repositório está sob `google-github-actions`, declara autoria Google LLC e licença Apache-2.0. O README recomenda uma chave `GEMINI_API_KEY` guardada em Actions Secrets; também há opções de autenticação Google Cloud/Vertex.

### O que ela acrescenta

- Interface por comentários em Issues e Pull Requests para pedir triagem, revisão, análise ou alterações.
- Workflows de plano e execução com um ciclo de aprovação de plano.
- Acesso configurável às ferramentas, incluindo ferramentas GitHub MCP; não é execução offline e depende de runner hospedado, rede e quota do modelo.

### Limites de segurança para o Nivus

- A implementação atual executa `gemini --yolo`; ferramentas que forem disponibilizadas ao CLI recebem aprovação automática durante aquele job. A proteção precisa estar na lista explícita de ferramentas e no escopo curto do token, não numa confirmação interativa em cada comando.
- O exemplo de invocação somente leitura dá acesso de escrita a Issues e Pull Requests para comentários. O exemplo `plan-execute` concede `contents: write` e disponibiliza operações de criar/editar/apagar arquivos e enviar commits.
- A Action instala `@google/gemini-cli@latest` por padrão. Para execução reproduzível, fixe a versão da Action por SHA revisado e configure uma versão exata do CLI; não instale extensions sem revisão.
- Conteúdo de Issue, comentários, diffs e arquivos do repositório é entrada não confiável e pode conter instruções maliciosas. Não passe segredos de produção, dados domésticos ou telemetria real ao agente. Evite debug e upload de artefatos quando a saída puder conter contexto privado.

### Decisão para esta arquitetura

A Action é uma boa candidata opcional para **revisão, triagem e planejamento sem permissão de escrita no código**, em runner hospedado. Não substitui o executor Nivus atual: esse worker limita caminhos, aplica patches validados, executa CI sem a chave e abre PR em rascunho. Se no futuro a Action for usada para gerar código, a versão Nivus deve manter runner descartável, ferramenta GitHub com allowlist, chave somente no job de inferência, branch/PR isolado, CI sem chave e revisão humana. Nenhum workflow da Action foi habilitado por esta avaliação.

A referência consultada estava no commit `387c8ddb7a72078825da941758b811b9153c71e8`; a release marcada mais recente era `v0.1.22`. Esses identificadores são uma fotografia de 2026-11-15 e devem ser conferidos antes de uma instalação. Consulte [metadados da Action](https://github.com/google-github-actions/run-gemini-cli/blob/387c8ddb7a72078825da941758b811b9153c71e8/action.yml), [README](https://github.com/google-github-actions/run-gemini-cli/blob/387c8ddb7a72078825da941758b811b9153c71e8/README.md) e [exemplo plan-execute](https://github.com/google-github-actions/run-gemini-cli/blob/387c8ddb7a72078825da941758b811b9153c71e8/examples/workflows/gemini-assistant/gemini-plan-execute.yml).
