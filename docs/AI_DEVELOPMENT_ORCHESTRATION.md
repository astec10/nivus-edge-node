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

## Notebook como servidor de controle

O CCE U25 pode atuar como **controlador leve sempre ligado**, sem executar código enviado por agentes. O controlador pode consultar tarefas aprovadas no GitHub, disparar um workflow hospedado, acompanhar o resultado e retomar a consulta após reinicialização. GitHub Issues e Actions permanecem como registro durável: se o notebook ficar offline, novas execuções aguardam; o estado existente não se perde.

```text
GitHub Issue revisada e marcada ai:ready
  -> controlador opcional no notebook (HTTPS de saída)
  -> GitHub Actions ubuntu-24.04 descartável
  -> agente/modelo autorizado e sandbox
  -> PR -> CI -> revisão humana
```

O controlador não precisa receber conexões da Internet, acessar o banco de telemetria nem expor portas. Uma conta de serviço separada deve ter somente acesso ao repositório necessário para ler as tarefas e disparar workflows. O token fica em credencial local de permissões restritas, nunca em issue, log, repositório ou prompt. Telemetria do Nivus não é dependência deste fluxo; agregação entre nós será útil quando o Nó Master estiver operacional.

Com os recursos informados para o CCE U25 (2 núcleos e cerca de 3,2 GiB de RAM), ele não é o local recomendado para manter agentes de código, builds paralelos ou sandboxes. Um runner padrão `ubuntu-24.04` hospedado pelo GitHub oferece 4 vCPU e 16 GB de RAM para repositórios públicos, com uso padrão gratuito segundo a documentação atual. Isso fornece computação, não créditos de modelo. O notebook pode coordenar; o runner hospedado executa.

Não configure um runner self-hosted GitHub no CCE para executar código de PRs públicos. O GitHub alerta que workflows com código não confiável podem comprometer o host e acessar credenciais. Se o notebook parar, o despacho pausa e retoma depois; isso não significa execução literalmente ininterrupta.

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

