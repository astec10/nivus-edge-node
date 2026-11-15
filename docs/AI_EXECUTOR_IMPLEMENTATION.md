# Executor de tarefas de desenvolvimento com IA

Este executor é infraestrutura de desenvolvimento para o repositório. Não roda no runtime do nó Nivus nem é o scheduler multi-nó da Fase 5.

## Estado

### Implementado nesta primeira etapa

- Formulário estruturado em GitHub Issues com objetivo, aceite, caminhos permitidos, risco, classificação de dados, limite de tempo, orçamento e responsável humano.
- Validador sem dependências externas que lê o texto como entrada não confiável e recusa caminhos perigosos ou escopo aberto.
- Workflow manual em runner GitHub-hosted que valida uma issue e coloca a label `ai:queued` como estado persistente.
- A execução do workflow não chama modelos, não faz checkout do código da issue, não roda comandos enviados no issue e não escreve código.

Esse intake é a primeira peça do executor, não um worker de código completo. Ele mantém uma tarefa estruturada e validada no GitHub, mas ainda não encaminha conteúdo a um modelo.

### Ainda não implementado

- Worker de modelo que reserve uma issue e produza alterações.
- Integração de Discord, Jira, Hermes ou OmniRoute.
- Lease/lock distribuído, sandbox de código, limites reais de tokens/custo e criação automática de PR.
- Credenciais de provedor ou de GitHub App. Nenhum segredo foi criado ou adicionado.

## Como usar a fila de entrada

1. Crie uma issue usando `AI development task` e forneça critérios de aceite e caminhos específicos.
2. Mantenha o conteúdo público e sem credenciais, dados da casa ou arquivos privados.
3. Um mantenedor executa **Actions → AI task intake → Run workflow**, informa o número da issue e confirma a revisão manual do conteúdo.
4. O workflow valida os campos e adiciona `ai:queued`. Essa label significa “validada, aguardando um worker”; ainda não significa que uma IA executou a tarefa.
5. Quando houver um worker configurado, ele só poderá reivindicar issues explicitamente colocadas na fila e autorizadas pela política.

## Próxima etapa de implementação

Usar o notebook CCE como controlador leve opcional e GitHub Actions como executor descartável. O controlador consultaria Issues revisadas e marcadas `ai:ready`, dispararia o workflow e registraria o identificador da execução; o runner hospedado executaria a tarefa. A fila durável continua no GitHub. Se o notebook estiver offline, o despacho pausa e retoma quando ele voltar. Telemetria não é pré-requisito; agregação entre nós passa a ser útil quando o Nó Master estiver operacional.

Para repositórios públicos, a documentação atual do GitHub informa runner padrão `ubuntu-24.04` com 4 vCPU e 16 GB de RAM, sem cobrança de uso padrão. Isso não fornece quota de LLM. A automação de código precisa de provedor/modelo e limites próprios de gasto.

Para ativar escrita automática ainda será necessário escolher: (a) provedor/modelo e orçamento máximo por tarefa/mês; (b) credencial GitHub de escopo mínimo; e (c) política de dados enviada ao modelo. O worker deve usar checkout efêmero, permissões mínimas, lease/idempotência, tentativas limitadas e abrir PR; não pode aprovar, fazer merge ou publicar em produção.

## Host e segurança

- O CCE U25 reportado tem 2 núcleos e cerca de 3,2 GiB RAM. Pode hospedar um controlador leve, mas builds, agentes e sandboxes devem ficar em runner hospedado/efêmero.
- Não configure runner self-hosted no repositório público: código enviado por forks pode comprometer o host e credenciais.
- A documentação do Hermes informa ao menos 1 GB para o container básico, 2–4 GB com navegador e 5 GB padrão na sandbox de ferramentas. Não instale o sandbox de agente no CCE sem medir recursos e isolamento.
- Não use `pull_request_target` para executar código de pull requests não confiáveis.
- Não use contas adicionais para contornar quotas/termos de fornecedores. Um roteador não cria tokens gratuitos.
- Persistência significa que a issue continua registrada e pode ser retomada depois; não é promessa de execução ilimitada ou sem falhas.

Fontes de referência e estado atualizado estão em [`AI_DEVELOPMENT_ORCHESTRATION.md`](AI_DEVELOPMENT_ORCHESTRATION.md) e [`AI_WORKFLOW.md`](AI_WORKFLOW.md).

