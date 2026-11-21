# Executor de tarefas de desenvolvimento com IA

Este executor é infraestrutura de desenvolvimento do repositório. Não roda no runtime do nó Nivus e não é o scheduler multi-nó da Fase 5.

## Estado verificado em 2026-11-16

- O fluxo inicial foi integrado ao `main` no PR #3. Ele valida tarefas públicas/sintéticas em GitHub Issues, restringe alterações a caminhos aprovados e cria um PR em rascunho depois da CI.
- A chave `GEMINI_API_KEY` e a variável `NIVUS_AI_BUDGET_MODE=free-tier` foram configuradas no GitHub segundo confirmação do mantenedor. O valor da chave nunca foi lido ou enviado ao chat. O mantenedor informou que usa um projeto Google sem faturamento; isso é uma configuração externa e não pode ser verificada pelo executor.
- Duas tentativas reais anteriores não produziram proposta: a primeira recebeu HTTP 503; a segunda terminou no timeout de 75 segundos da chamada síncrona e foi exibida incorretamente como `None`.
- O adaptador atual envia uma única chamada, consulta interações em segundo plano por até quatro minutos, registra metadados sanitizados e tenta excluir a interação; os testes simulados cobrem sucesso, falha, timeout e exclusão. Uma chamada explicitamente autorizada para a Issue #6 gerou a proposta documental do PR #16. A validação do PR passou, mas a etapa de abertura automática falhou porque `gh repo view` exige um checkout; o mantenedor abriu o draft manualmente. A workflow principal foi corrigida no commit `bec9573` para ler o branch padrão pela API sem checkout. O PR #53 adicionou um guard que detecta um draft aberto para a mesma issue antes de chamar o modelo, além de limpar `ai:ready`/`ai:queued` e comentar o link quando cria um draft. O PR #53 passou os checks hospedados; na issue #6 existente, o guard pularia a chamada porque o PR #16 já está aberto. Ainda não houve nova chamada autorizada para confirmar o fluxo completo de abertura automática.
- O executor não aprova, faz merge, implanta ou controla dispositivos domésticos. A revisão humana continua obrigatória.

## Implementação e limites

- O intake valida o formulário da Issue e a classificação de dados antes de enfileirar a tarefa.
- O adaptador em `tools/ai_executor/gemini_client.py` usa `gemini-3.8-flash` e a API Interactions. A chamada `POST` não é repetida automaticamente; respostas em andamento são consultadas por `GET` até o limite de 4 minutos. Cada requisição HTTP tem timeout próprio de até 30 segundos.
- A execução em segundo plano da API exige armazenamento temporário. O adaptador envia `store=true`, consulta o estado e tenta cancelar tarefas ainda ativas no timeout; em seguida tenta `DELETE` da interação. O relatório de uso indica `interaction_deleted`. Se o provedor não aceitar a exclusão, o registro pode permanecer segundo a retenção da API; no plano gratuito documentado atualmente, a retenção padrão é de um dia.
- O relatório de uso não inclui prompt, resposta nem chave. Ele inclui estado, duração, código de erro, uso de tokens, ID da interação e resultado da tentativa de exclusão; o artefato do Actions fica retido por 30 dias.
- O conteúdo enviado pode ser usado pelo Google para melhorar seus produtos no plano gratuito. Use exclusivamente código público e dados sintéticos; nunca inclua segredos, bancos, telemetria real, dados domésticos, rostos ou informações pessoais.
- A variável `NIVUS_AI_BUDGET_MODE=free-tier` confirma a intenção do mantenedor, mas não impõe limite financeiro. A configuração de faturamento precisa ser conferida no projeto Google separado.
- O intake autorizado inicia o worker somente pelo evento de adicionar a label `ai:ready`. Ele não chama também `workflow_dispatch`, evitando duas chamadas acidentais para uma autorização. O despacho manual do workflow do worker continua sendo um caminho independente e requer a confirmação explícita `reviewed_and_authorized=true`.
- O worker não executa comandos sugeridos pela Issue/modelo; valida e aplica somente arquivos completos nos caminhos exatos permitidos. CI roda em outro runner, sem a chave Gemini. Uma pessoa revisa o PR e aprova qualquer merge.

## Compatibilidade do runtime das GitHub Actions

O worker atual usa `actions/checkout@v7`, `actions/setup-python@v7` e `actions/upload-artifact@v7`. Os metadados dessas versões declaram `runs.using: node24`, portanto as Actions do worker já acompanham a transição do Node 20 para Node 24. Uma execução antiga pode continuar mostrando o aviso de depreciação nos logs daquele run. Esse aviso é separado do erro `interaction_failed`: esse código significa que a API Gemini informou estado terminal `failed` para a interação, mas, sozinho, não identifica a causa no provedor. O controlador do notebook não repete chamadas nem faz inferência; outra tentativa requer nova autorização explícita depois de revisar o estado e os metadados sanitizados.

Referências de runtime: [checkout v7](https://github.com/actions/checkout/blob/v7/action.yml), [setup-python v7](https://github.com/actions/setup-python/blob/v7/action.yml) e [upload-artifact v7](https://github.com/actions/upload-artifact/blob/v7/action.yml).

## Diagnóstico dos runs da Issue #80

A [tentativa 1 do run #7](https://github.com/astec10/nivus-edge-node/actions/runs/44236019706/attempts/1) e o [run #6](https://github.com/astec10/nivus-edge-node/actions/runs/44235610603) terminam em `interaction_failed`: a interação Gemini chegou ao estado terminal `failed`, sem expor a causa interna do provedor. A [tentativa 2 do run #7](https://github.com/astec10/nivus-edge-node/actions/runs/44236019706/attempts/2) parou antes do modelo com `issue_missing_ai_queue_labels`, pois os rótulos já não estavam na Issue. Esses logs antigos resolveram checkout@v4, setup-python@v5 e upload-artifact@v4, o que gerou o aviso de Node 20. A versão atual do workflow usa versões v7 cujo metadata declara runtime Node 24; o aviso de depreciação está corrigido na fonte atual. O erro do provedor permanece sem causa identificada e não deve ser repetido sem nova autorização humana.

## Como usar a fila

1. Crie uma Issue usando o formulário `AI development task`, com critérios verificáveis e caminhos específicos.
2. Revise se todo o conteúdo é público ou sintético. Não use dados do notebook ou da casa.
3. Em **Actions → AI task intake → Run workflow**, informe o número da Issue e confirme a revisão do conteúdo. Sem autorização de modelo, o intake adiciona `ai:queued` e não chama Gemini.
4. No notebook, também é possível usar **Configuração → Executor GitHub** para configurar um token fine-grained com `Issues: Read and write`, testar a API e acompanhar a fila. O botão **Atualizar fila** executa uma consulta GET imediata ao GitHub; não chama o modelo nem altera Issues. O controlador permanece desligado até o administrador habilitá-lo. Sem notebook, o intake manual continua disponível no GitHub.
5. Para autorizar uma proposta, revise o conteúdo e confirme uma única chamada free-tier no intake ou no botão da dashboard. A dashboard aplica `ai:ready` uma vez; não repita a ação quando o resultado estiver incerto. O controlador aplica um limite configurável de 1–10 autorizações em 24 horas, padrão 3, somente para ações originadas na dashboard. Isso não é limite de cobrança do provedor nem cobre o disparo manual no GitHub.
6. O worker verifica labels e contrato, lê o contexto público e os caminhos aprovados, envia uma solicitação e produz uma proposta limitada. Se o provedor falhar, a Issue permanece registrada e o relatório contém somente metadados sanitizados.
7. Se a tentativa falhar e for apropriado tentar novamente, faça uma nova autorização explícita pelo intake do GitHub após confirmar o estado do workflow. O controlador não repete automaticamente chamadas nem altera `ai:ready`.
8. Revise o diff e o resultado da CI no PR em rascunho. O worker nunca aprova, faz merge ou deploy.

## Próximo marco

O controlador notebook está implementado no [PR #93](https://github.com/astec10/nivus-edge-node/pull/93), aberto para revisão e sem status de rascunho. O código funcional passou nos quatro workflows no head `9806601`. A última verificação do head documental anterior mostrou três workflows concluídos e Ubuntu VM validation em andamento; esta atualização aciona nova CI. Ainda sem merge, instalação ou validação no host; a dashboard instalada não tem confirmação de execução desse painel. O PR #16 da Issue #6 continua em rascunho para revisão humana; seus checks hospedados passaram. Nenhuma nova chamada de modelo foi feita neste trabalho. A CI hospedada não certifica hardware, conexão pela ONU ou reboot do host.

Issues e GitHub Actions são o estado durável e o executor principal; nenhuma máquina do operador precisa ficar ligada. O notebook CCE é suporte opcional para análise e relatórios, não um runner self-hosted para um repositório público.

## Referências externas

- [Gemini Interactions API](https://ai.google.dev/gemini-api/docs/interactions-overview)
- [Gemini background execution, polling, cancelamento e exclusão](https://ai.google.dev/gemini-api/docs/background-execution)
- [Gemini Interactions API reference](https://ai.google.dev/api/interactions-api)

## Permissão para criar PR

A etapa final usa `gh pr create --draft` com o `GITHUB_TOKEN`. Confira **Settings → Actions → General → Workflow permissions → Allow GitHub Actions to create and approve pull requests**. Sem essa permissão, a branch e a CI podem concluir, mas um mantenedor precisará criar o PR manualmente. O workflow solicita permissão de escrita para PR somente no job de abertura; não contém etapas de aprovação, merge ou deploy.


## Executor de inferência no runtime do Nivus (separado)

O cadastro de perfis de IA e o endpoint de inferência do runtime são distintos do worker GitHub Actions documentado acima. O endpoint runtime exige administrador e usa um perfil explicitamente selecionado; não executa o código/texto gerado, não faz fallback e não compartilha GEMINI_API_KEY.

A integração da issue #74 foi integrada pelo PR #82 e está na `main` atual. A chave de provedor é descriptografada em memória; budgets/quota são reservados antes da chamada; prompt e resposta não são persistidos; e a auditoria registra apenas metadados sanitizados. Os checks CI usam mocks; nenhum provedor real foi chamado. A implantação no notebook não foi confirmada. A estimativa local depende das tarifas manuais verificadas pelo administrador e deve ser acompanhada por teto de gasto configurado no próprio serviço.
