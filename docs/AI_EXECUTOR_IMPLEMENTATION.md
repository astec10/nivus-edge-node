# Executor de tarefas de desenvolvimento com IA

Este executor é infraestrutura de desenvolvimento para o repositório. Não roda no runtime do nó Nivus nem é o scheduler multi-nó da Fase 5.

## Estado

### Implementado nesta primeira etapa

- Formulário estruturado em GitHub Issues com objetivo, aceite, caminhos permitidos, risco, classificação de dados, limite de tempo, orçamento e responsável humano.
- Validador sem dependências externas que lê o texto como entrada não confiável e recusa caminhos perigosos ou escopo aberto.
- Workflow manual em runner GitHub-hosted que valida uma issue e coloca a label `ai:queued` como estado persistente.
- Adaptador isolado para Gemini Interactions em `tools/ai_executor/gemini_client.py`. Ele aceita tarefa/contexto fornecidos pelo chamador e devolve uma proposta JSON; verifica paths contra allowlist exata, não escreve arquivos e não executa comandos.
- Worker e workflow de proposta em `tools/ai_executor/worker.py` e `.github/workflows/ai-proposal-worker.yml`. A execução só começa quando alguém com permissão coloca `ai:ready` numa issue já validada, ou confirma explicitamente a chamada free-tier no despacho manual.
- O worker carrega o contexto público do projeto, lê os arquivos exatos permitidos, recusa conteúdo que pareça credencial e aplica somente a proposta dentro da allowlist. O workflow publica o branch, roda CI num job/runner separado sem a chave Gemini e abre um PR em rascunho somente após CI aprovada. O conteúdo gerado não é executado no job que possui a chave.
- Cada tentativa prepara um artefato de uso com modelo, estado, duração, ID da interação e contagens de tokens; não inclui prompt, resposta ou chave e fica retido por 30 dias no GitHub Actions.
- O intake e o worker aceitam somente a branch padrão; o worker limita a execução ao tempo solicitado na Issue (1–15 minutos), bloqueia alterações de workflows e usa somente `gemini-3.8-flash`.
- Oito testes unitários sem rede cobrem o contrato da Issue, autorização, tempo máximo, bloqueio de workflows, allowlist, gravação limitada e recusa segura quando falta a chave; a CI do Ubuntu executará essa suíte.

O executor está sendo preparado para o PR #3 e ainda não está ativo no `main`. A API não foi chamada: ainda não há chave `GEMINI_API_KEY`, variável de orçamento nem execução end-to-end observada. Portanto, o fluxo não pode ser descrito como executor operacional até esses passos passarem.

### Falta para ativar e validar

- Revisar e integrar o PR #3, que reúne o executor com a documentação e automação de manutenção.
- Depois do merge, criar um projeto Google separado sem faturamento vinculado; guardar a chave em GitHub Actions Secrets como `GEMINI_API_KEY` e definir `NIVUS_AI_BUDGET_MODE=free-tier`. A variável é uma declaração operacional e não confere o estado de faturamento; o código não bloqueia cobrança caso a chave esteja associada a um projeto faturável. Não envie a chave no chat, Issue ou repositório.
- Executar uma tarefa pequena, pública/sintética, com um único caminho permitido; confirmar artefato de uso, PR em rascunho, CI e revisão humana.
- Integração de Discord, Jira, Hermes ou OmniRoute.
- Router para outros provedores/modelos, leases além do `concurrency` por Issue e política de tentativas limitadas após esgotamento da quota.
- Credenciais de provedor. Nenhum segredo foi criado ou adicionado.

## Como usar a fila de entrada

1. Crie uma issue usando `AI development task` e forneça critérios de aceite e caminhos específicos.
2. Mantenha o conteúdo público e sem credenciais, dados da casa ou arquivos privados.
3. Um mantenedor executa **Actions → AI task intake → Run workflow**, informa o número e confirma que revisou o conteúdo. O intake valida os campos e adiciona `ai:queued`.
4. Para pedir uma chamada de modelo, selecione o orçamento `free-tier model call — public/synthetic content only`; execute novamente **AI task intake** com `authorize_free_model_call=true` depois de revisar a Issue. O intake adiciona `ai:ready` e dispara explicitamente uma tentativa. A tarefa precisa conter somente material público/sintético. A seleção no formulário, sozinha, não chama o modelo.
5. O worker verifica as labels, contrato, risco e dados; limita a leitura aos documentos base e aos caminhos exatos da Issue. Se aprovado, prepara branch e PR em rascunho. Se quota/configuração falhar, a Issue permanece no GitHub e o artefato registra somente metadados sanitizados.
6. Um humano revisa o PR e CI. O worker não aprova, faz merge, publica em produção nem executa atuadores domésticos.

## Próxima etapa de implementação

GitHub Issues é a fila durável e GitHub Actions é o executor principal; nenhuma máquina do operador precisa ficar ligada. O gatilho `ai:ready` inicia o runner hospedado. O notebook é apenas suporte opcional para acompanhar a página de progresso, baixar/agregar artefatos de uso ou ajudar em análises locais. Se o notebook ou o PC do operador ficar desligado, a execução não pausa. A chamada ao modelo ainda depende de Internet, GitHub, quota Gemini e configuração válida. Telemetria não é pré-requisito; agregação entre nós será útil quando o Nó Master estiver operacional.

Para repositórios públicos, a documentação atual do GitHub informa runner padrão `ubuntu-24.04` com 4 vCPU e 16 GB de RAM, sem cobrança de uso padrão. Isso não fornece quota de LLM. A automação de código precisa de provedor/modelo e limites próprios de gasto.

O único modelo habilitado nesta versão é `gemini-3.8-flash` pela Gemini Interactions API. O adaptador requer `NIVUS_AI_BUDGET_MODE=free-tier`, limita tokens/tempo, recusa redirecionamentos HTTP, não repete chamadas automaticamente e solicita `store: false`. A cota gratuita pode mudar e pausar chamadas; o worker não tenta contornar limites. A variável de orçamento não é um limitador técnico de cobrança. Use projeto Google sem faturamento vinculado. Na modalidade gratuita, o Google informa que o conteúdo pode ser usado para melhorar seus produtos. Envie somente código público e contexto sanitizado; nunca segredos, bancos, telemetria real, dados domésticos ou informações pessoais.

## Host e segurança

- O CCE U25 reportado tem 2 núcleos e cerca de 3,2 GiB RAM. Ele pode agregar relatórios ou servir como console quando estiver online, mas o executor principal não depende dele; builds e tarefas rodam em runners hospedados efêmeros.
- Não configure runner self-hosted no repositório público: código enviado por forks pode comprometer o host e credenciais.
- A documentação do Hermes informa ao menos 1 GB para o container básico, 2–4 GB com navegador e 5 GB padrão na sandbox de ferramentas. Não instale o sandbox de agente no CCE sem medir recursos e isolamento.
- Não use `pull_request_target` para executar código de pull requests não confiáveis.
- Não use contas adicionais para contornar quotas/termos de fornecedores. Um roteador não cria tokens gratuitos.
- Persistência significa que a issue continua registrada e pode ser retomada depois; não é promessa de execução ilimitada ou sem falhas.

Fontes de referência e estado atualizado estão em [`AI_DEVELOPMENT_ORCHESTRATION.md`](AI_DEVELOPMENT_ORCHESTRATION.md) e [`AI_WORKFLOW.md`](AI_WORKFLOW.md).
