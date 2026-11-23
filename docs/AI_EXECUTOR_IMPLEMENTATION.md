# Executor de tarefas de desenvolvimento com IA

Este executor roda no GitHub Actions para preparar propostas de alterações no repositório. Ele é separado da inferência local da dashboard e do futuro scheduler de tarefas entre nós. O notebook não precisa ficar ligado para a CI hospedada executar.

## Estado da migração — 2026-11-23

O PR #139 é uma proposta em rascunho da Issue #138. Ainda não foi mesclado; a branch `main` continua com o worker Gemini. Não houve chamada real ao Gemini ou ao OpenRouter para preparar este PR. Os testes do cliente usam respostas simuladas.

A Issue #137 está sem `ai:ready` e permanece desarmada até a revisão/merge do PR, configuração do segredo no GitHub e uma autorização humana posterior. A variável de orçamento sozinha não substitui nem cria a chave.

## OpenRouter Free proposto para o worker

- Endpoint fixo: `https://openrouter.ai/api/v1/chat/completions`.
- Rota fixa: `openrouter/free`; o código não aceita selecionar um modelo pago.
- Uma autorização pode produzir no máximo uma requisição HTTP. Não há retry, fallback da aplicação, execução paralela nem redirecionamento com a chave.
- O payload pede JSON estruturado. O worker valida formato, tamanho e caminhos exatos da allowlist antes de aplicar a proposta.
- Relatórios e mensagens de erro registram códigos e metadados limitados; não incluem prompts, respostas, chave ou detalhes locais do sistema de arquivos.
- Se a geração, validação da proposta ou abertura do PR falhar, o workflow remove `ai:ready`, publica um código de erro sanitizado e o link do run. Não inicia uma nova tentativa automaticamente.
- Use somente código público e dados sintéticos. Não envie segredos, bancos, telemetria real, dados da casa ou informações pessoais.

### Configuração após a revisão

Depois do merge, o mantenedor configura diretamente no repositório GitHub:

1. **Settings → Secrets and variables → Actions → New repository secret**: nome `OPENROUTER_API_KEY`, com o valor guardado no GitHub, nunca no chat, issue ou código.
2. **Settings → Secrets and variables → Actions → Variables**: `NIVUS_AI_BUDGET_MODE=free-tier`.

A chave ausente ou a variável ausente fazem o worker parar antes da requisição. A variável é uma trava de intenção no código, não um teto financeiro configurado pelo provedor.

A documentação oficial consultada em 23/11/2026 descreve `openrouter/free` como uma rota de preço de modelo zero que escolhe entre modelos gratuitos disponíveis. A coleção Free Models informa limites atuais de 20 requisições por minuto e 50 por dia para contas sem créditos; tentativas com falha também contam para a cota diária. A lista, disponibilidade e limites podem mudar. Confira [Free Models Router](https://openrouter.ai/openrouter/free) e [Free Models](https://openrouter.ai/collections/free-models/) antes de cada marco. O projeto não compra créditos nem habilita fallback pago.

## Fluxo de uso após merge

1. Crie uma issue pelo formulário de tarefa de desenvolvimento com critérios verificáveis e caminhos exatos permitidos.
2. Revise a classificação e confirme que o conteúdo é público/sintético.
3. O intake pode colocar a issue em `ai:queued` sem chamar um modelo.
4. Depois de revisar a issue e conferir configuração/cota, autorize a execução. A label `ai:ready` inicia o worker para aquela autorização.
5. O worker cria uma proposta limitada, a CI a valida e o workflow abre um PR em rascunho. Em qualquer falha, a issue é desarmada e recebe um código sanitizado.
6. Uma pessoa revisa o diff e aprova merge ou implantação. O executor não aprova, mescla ou implanta código.

Não autorize uma nova chamada automaticamente após falha. Cada autorização consome uma tentativa única e pode consumir a cota do serviço, mesmo quando o provedor falha.

## Referências do worker atual

O fluxo Gemini e seus registros históricos permanecem na implementação do adaptador em `tools/ai_executor/gemini_client.py` e em commits anteriores. Eles descrevem execuções anteriores, não o comportamento proposto no PR #139. A migração atual substitui a integração do worker GitHub Actions; não altera os perfis de IA de runtime.

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

