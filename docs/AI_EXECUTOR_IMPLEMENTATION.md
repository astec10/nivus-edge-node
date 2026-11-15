# Executor de tarefas de desenvolvimento com IA

Este executor é infraestrutura de desenvolvimento do repositório. Não roda no runtime do nó Nivus e não é o scheduler multi-nó da Fase 5.

## Estado verificado em 2026-11-15

- O fluxo inicial foi integrado ao `main` no PR #3. Ele valida tarefas públicas/sintéticas em GitHub Issues, restringe alterações a caminhos aprovados e cria um PR em rascunho depois da CI.
- A chave `GEMINI_API_KEY` e a variável `NIVUS_AI_BUDGET_MODE=free-tier` foram configuradas no GitHub segundo confirmação do mantenedor. O valor da chave nunca foi lido ou enviado ao chat. O mantenedor informou que usa um projeto Google sem faturamento; isso é uma configuração externa e não pode ser verificada pelo executor.
- Duas tentativas reais anteriores não produziram proposta: a primeira recebeu HTTP 503; a segunda terminou no timeout de 75 segundos da chamada síncrona e foi exibida incorretamente como `None`.
- Esta alteração troca a chamada síncrona por execução Gemini em segundo plano com polling limitado, erros sanitizados com código estável e exclusão da interação depois de recuperar a resposta. Os testes locais simulados passaram; a chamada end-to-end com este código ainda depende de CI/PR e de uma nova execução autorizada.
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

O marco imediato é confirmar uma proposta end-to-end usando uma Issue pública/sintética, verificar que o relatório mostra uso de tokens e `interaction_deleted=true`, e confirmar que a CI passa antes de criar um PR em rascunho. Depois disso, a próxima entrega documentada é a Fase 1 de portabilidade/recuperação: primeiro concluir a verificação hospedada dos PRs de sensores e dashboard; não usar VMs no computador do operador. CI em runner remoto não certifica hardware Intel/AMD nem sensores físicos.

Issues e GitHub Actions são o estado durável e o executor principal; nenhuma máquina do operador precisa ficar ligada. O notebook CCE é suporte opcional para análise e relatórios, não um runner self-hosted para um repositório público.

## Referências externas

- [Gemini Interactions API](https://ai.google.dev/gemini-api/docs/interactions-overview)
- [Gemini background execution, polling, cancelamento e exclusão](https://ai.google.dev/gemini-api/docs/background-execution)
- [Gemini Interactions API reference](https://ai.google.dev/api/interactions-api)

## Permissão para criar PR

A etapa final usa `gh pr create --draft` com o `GITHUB_TOKEN`. Confira **Settings → Actions → General → Workflow permissions → Allow GitHub Actions to create and approve pull requests**. Sem essa permissão, a branch e a CI podem concluir, mas um mantenedor precisará criar o PR manualmente. O workflow solicita permissão de escrita para PR somente no job de abertura; não contém etapas de aprovação, merge ou deploy.
