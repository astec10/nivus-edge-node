# Conexões com provedores de IA

Estado: o cadastro administrativo foi integrado no PR #72 e está incluído na release `f896de8` aplicada no notebook. O executor runtime da issue #74 foi integrado no PR #82 e está na `main` atual; os checks hospedados passaram. Nenhuma chamada real a modelo foi feita, e não há confirmação de implantação do PR #82 no notebook.

## Onde encontrar e como usar

A tela fica em **Configuração → Provedores de IA** e é visível somente para administradores. A experiência começa pela lista de conexões existentes. **Adicionar provedor** abre um formulário; a seleção do catálogo preenche os campos conhecidos, e **Cadastro manual** abre os campos de endpoint e protocolo compatível. Um cadastro novo começa desabilitado.

O formulário registra:

- provedor ou nome manual, protocolo, tipo de endpoint e URL-base;
- modelo escolhido, responsável pelo serviço ou cobrança e finalidade;
- autenticação, chave, orçamento mensal, preços de entrada/saída por milhão de tokens e data de conferência, limite de solicitações por hora e timeout;
- classes de dados permitidas.

Para provedores em nuvem, o administrador informa manualmente o custo de entrada e saída por milhão de tokens e a data em que conferiu a tabela oficial. O executor bloqueia a nuvem se esses valores estiverem ausentes ou tiverem mais de 90 dias. Os preços não são buscados automaticamente e devem ser atualizados pelo responsável.

O catálogo inicial inclui OpenAI, Anthropic, Google Gemini e Ollama local. O cadastro manual aceita os protocolos suportados pela API. Edite nome, modelo, responsável, finalidade, política e limites diretamente na lista. Para trocar endpoint/protocolo, remova este perfil e cadastre-o de novo. A chave tem ação separada de substituição. O painel mostra somente se há uma credencial configurada, nunca o valor salvo.

Salvar não faz conexão. A ação **Testar conexão** é explícita e exige confirmação para nuvem. Ela faz uma requisição GET à lista de modelos do endpoint (Ollama usa `/api/tags`), com timeout; não envia prompt nem dados do Nivus. Uma consulta pode consumir cota do provedor. Antes do teste de nuvem, é obrigatório configurar um orçamento mensal maior que zero; cada tentativa externa consome uma solicitação do limite por hora. O valor mensal é uma política registrada, não uma medição ou bloqueio de gasto. Um perfil só pode ser habilitado depois de um teste bem-sucedido e, para nuvem, de um orçamento mensal maior que zero. Nenhum perfil é habilitado automaticamente.

## Proteção da chave

Chave de API não pode ser guardada apenas como hash: o processo precisa recuperar o segredo para autenticar uma chamada. Por isso, a API cifra a credencial antes de gravá-la em SQLite com AES-GCM da biblioteca `cryptography`. A cifra usa nonce aleatório de 96 bits e associa o identificador do perfil como dado autenticado. O backend nunca inclui a chave ou o texto cifrado na resposta da API, no log ou na auditoria; o navegador só recebe `credential_configured`.

A chave mestra é um arquivo binário de 32 bytes, instalado em `/etc/nivus-compose/secrets/provider_encryption_key`, fora do repositório e do SQLite, com proprietário root, grupo de runtime e modo 0440. O instalador a cria uma única vez. O atualizador preserva a chave; se encontrar credenciais cifradas sem a chave, interrompe antes de trocar a release. Não substitua uma chave existente: isso inutiliza as credenciais cifradas. A interface ainda não oferece rotação da chave mestra; para rotacioná-la será necessário um procedimento futuro que re-cifre todos os registros com backup protegido.

O backup normal do SQLite não contém a chave mestra. Para recuperar perfis em outro host, restaure o mesmo arquivo de chave por um canal offline protegido, com o proprietário, grupo e permissões corretos, antes de iniciar a API. Guarde a cópia de recuperação separada do backup de dados e fora do GitHub. Perder a chave exige cadastrar credenciais novas.

## Nuvem, rede local e dados

- Endpoints de nuvem exigem HTTPS na porta 443. O teste valida que DNS resolve para endereços públicos, fixa o endereço resolvido durante a conexão e bloqueia redirecionamentos.
- Modelos locais usam somente HTTP em endereços privados, sem loopback, link-local ou endereços especiais, e portas limitadas ao protocolo cadastrado. Ollama usa 11434; endpoints OpenAI compatíveis aceitam as portas 1234 e 8000. A conexão local não envia chave por HTTP.
- Nuvem aceita apenas as classes `public` e `synthetic`. Dados pessoais, de operação do nó, da casa e de câmeras são recusados pela API para provedores de nuvem.
- A auditoria registra ator, ação, estado e horário sem chave, prompt ou resposta.

O executor de inferência da issue #74 aplica o limite por hora em conjunto com os testes de conexão. Antes de cada chamada, reserva o custo estimado no orçamento mensal e no orçamento acumulado da tarefa. Provedores de nuvem exigem preços de entrada/saída por milhão de tokens configurados pelo administrador e conferidos nos últimos 90 dias; sem preços, orçamento ou classe de dados permitida, a chamada é bloqueada. O cálculo usa o tamanho UTF-8 da entrada com margem conservadora, a saída máxima permitida e, após a resposta, o uso de tokens informado pelo provedor. Esse executor foi integrado pelo PR #82 e os checks hospedados passaram; isso não equivale a uma chamada real nem a implantação no notebook.

Esse bloqueio é um limite local estimado, não uma fatura do provedor: tarifação por cache, ajustes da conta, mudanças de preço ou metadados internos do serviço podem diferir. Configure também um limite de gastos na conta do provedor. Em timeout ou cancelamento depois do envio, a reserva é mantida porque a cobrança pode ser incerta.

## Execução explícita de uma tarefa

A rota administrativa `POST /api/ai/executor/complete` executa uma solicitação para um único perfil selecionado pelo chamador. O payload leva UUID de solicitação (idempotência), ID de tarefa, provedor, instrução, classe de dados, orçamento acumulado da tarefa e limite de tokens de saída. Não há roteamento implícito, fallback para outra nuvem nem repetição automática. Uma nova tentativa requer UUID novo.

A inferência usa os protocolos OpenAI-compatible, Anthropic Messages, Gemini Interactions REST (com `store=false`) e Ollama Chat. O Gemini envia uma interação stateless, sem ferramentas; Generate Content permanece legado para novos projetos. Consulte [a referência oficial de Interactions](https://ai.google.dev/api/interactions-api) e [o guia oficial de migração](https://ai.google.dev/gemini-api/docs/interactions-breaking-changes-may-2026). Ferramentas/chamadas de função e execução do conteúdo gerado não estão habilitadas. A resposta é retornada ao chamador, mas prompt e saída não são gravados no SQLite, na auditoria ou nos logs. A auditoria registra somente IDs, ator, provedor/modelo, classe, estado, duração, tokens reportados, estimativa de custo e motivo de bloqueio.

A rota `POST /api/ai/executor/requests/{request_id}/cancel` fecha a conexão acompanhada e cancela o trabalho pendente local. Se a requisição já saiu do Nivus, o serviço externo ainda pode concluir e cobrar. Solicitações concluídas, desconhecidas ou de outro administrador não podem ser canceladas.

O runtime do executor foi integrado à `main` pelo PR #82, com CI aprovada. A última versão informada no notebook é `f896de8`, anterior a esse PR; a instalação do runtime permanece pendente de atualização reversível e validação no host. Os testes usam mocks e conteúdo sintético; não fazem chamadas reais de provedor.

## Relação com o executor GitHub Actions

Esta configuração pertence ao runtime do Nivus. Ela não lê nem altera `GEMINI_API_KEY` do GitHub Actions. O executor de desenvolvimento do GitHub continua com segredos próprios, permissões próprias e aprovação humana; não copiar chaves entre esses dois ambientes.

## Rotas e validação

As rotas administrativas ficam em `backend/api/routers/ai_providers.py`; a cifra, validação de endpoint, teste explícito e auditoria ficam em `backend/services/ai_providers.py`. A migração é aditiva e cria as tabelas `ai_provider_connections` e `ai_provider_audit`.

A CI do PR #72 passou nos workflows de smoke Compose Ubuntu 22.04, painel/sensores, índice e CodeQL; seu código está na release `f896de8`. O PR #82 integrou inferência runtime; seus checks hospedados e os workflows da `main` atual passaram. Os testes usam respostas simuladas e não fazem chamada real a provedor. A implantação do #82 no notebook continua pendente.
