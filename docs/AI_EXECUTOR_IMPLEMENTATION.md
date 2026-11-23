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

## Como usar a fila

1. Crie uma Issue usando o formulário `AI development task`, com critérios verificáveis e caminhos específicos.
2. Revise se todo o conteúdo é público ou sintético. Não use dados do notebook ou da casa.
3. Em **Actions → AI task intake → Run workflow**, informe o número da Issue e confirme a revisão do conteúdo. Sem autorização de modelo, o intake adiciona `ai:queued` e não chama Gemini.
4. Para autorizar uma proposta, marque `authorize_free_model_call=true` somente depois de revisar a Issue. O intake adiciona `ai:ready`; esse único evento inicia o worker. Não inicie outro workflow em paralelo para a mesma autorização.
5. O worker verifica labels e contrato, lê o contexto público e os caminhos aprovados, envia uma solicitação e produz uma proposta limitada. Se o provedor falhar, a Issue permanece registrada e o relatório contém somente metadados sanitizados.
6. Se a tentativa falhar e for apropriado tentar novamente, faça uma nova autorização explícita pelo intake; o fluxo remove a label anterior e a reaplica para emitir um único evento de execução.
7. Revise o diff e o resultado da CI no PR em rascunho. O worker nunca aprova, faz merge ou deploy.

## Próximo marco

O PR #16 continua em rascunho para revisão humana; os checks hospedados passaram. A proposta foi gerada, mas a abertura automática falhou naquela execução; `bec9573` corrigiu a leitura do branch e PR #53 acrescentou o guard de duplicação. Nenhuma nova chamada foi feita. Próximo marco: revisar o PR #16; depois, se necessário, autorizar uma nova issue pública/sintética para confirmar o ciclo automático, sem reutilizar a issue #6 enquanto o draft estiver aberto. Em paralelo, aplicar e conferir as mudanças de dashboard no notebook; CI hospedada não certifica hardware Intel/AMD nem sensores físicos.

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

## Transição do provedor de desenvolvimento — 2026-11-23

A execução da Issue #137 falhou na etapa Gemini com o código sanitizado `interaction_failed`. A Issue #137 foi desarmada: `ai:ready` foi removida e não houve nova chamada. A Issue #138 e o PR de bootstrap substituem o adaptador Gemini do **worker GitHub Actions** por OpenRouter Free. Isso não altera o runtime de inferência do Nivus nem o chat local-first da dashboard.

O candidato usa somente o endpoint fixo `https://openrouter.ai/api/v1/chat/completions` e o modelo de rota `openrouter/free`; não recebe uma lista de modelos pagos, não habilita fallback da aplicação e não repete a requisição após erro, timeout, limite ou resposta inválida. O cliente pede saída JSON estruturada, valida cada caminho contra a allowlist e registra apenas metadados sanitizados. Em falha, o workflow remove `ai:ready` e comenta o link do run. A CI usa respostas simuladas; nenhuma inferência real é feita pelo PR.

Para habilitar depois de revisar/mesclar o PR, o mantenedor cria uma chave em [OpenRouter API Keys](https://openrouter.ai/settings/keys) e salva diretamente em **Settings → Secrets and variables → Actions** como `OPENROUTER_API_KEY`. Não envie a chave no chat, Issue, código ou logs. O workflow também exige a variável `NIVUS_AI_BUDGET_MODE=free-tier`. Sem a chave, o worker para em preflight antes de chamar a rede.

A documentação oficial consultada em 23/11/2026 anuncia `openrouter/free` com preço de modelo zero e cadastro sem cartão; o roteador escolhe entre modelos gratuitos disponíveis, então a qualidade e disponibilidade podem variar. A coleção de modelos gratuitos informa limites atuais de 20 requisições por minuto e 50 por dia; chamadas com falha também contam no limite diário. Esses limites podem mudar. **Não compre créditos para aumentar a cota e não configure modelo pago/fallback.** Veja [OpenRouter Free Models](https://openrouter.ai/collections/free-models/) e [Free Models Router](https://openrouter.ai/openrouter/free).

Envie somente código público e dados sintéticos. O OpenRouter encaminha cada solicitação ao modelo gratuito disponível; revise as políticas e retenção dos provedores listados antes de enviar qualquer outro dado. Não inclua segredos, código privado, telemetria real, dados domésticos ou pessoais. A key antiga `GEMINI_API_KEY` deixa de ser lida pelo workflow após a integração; a remoção do segredo antigo no GitHub fica a cargo do mantenedor.

**Estado:** até o PR ser revisado/mesclado e a chave `OPENROUTER_API_KEY` ser cadastrada, a `main` continua no código anterior e o worker permanece sem uso para a Issue #137. Depois da configuração, uma única autorização é necessária para a próxima chamada gratuita. O PR não faz deploy no notebook.

