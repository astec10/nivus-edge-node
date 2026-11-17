# Conexões com provedores de IA

Estado: configuração administrativa em implementação na issue #68. O cadastro, por si só, não conecta o executor de tarefas nem envia prompts.

## Onde encontrar e como usar

A tela fica em **Configuração → Provedores de IA** e é visível somente para administradores. A experiência começa pela lista de conexões existentes. **Adicionar provedor** abre um formulário; a seleção do catálogo preenche os campos conhecidos, e **Cadastro manual** abre os campos de endpoint e protocolo compatível. Um cadastro novo começa desabilitado.

O formulário registra:

- provedor ou nome manual, protocolo, tipo de endpoint e URL-base;
- modelo escolhido, responsável pelo serviço ou cobrança e finalidade;
- autenticação, chave, orçamento mensal, limite de solicitações por hora e timeout;
- classes de dados permitidas.

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

Os campos de orçamento e solicitações por hora são **política armazenada**, não um medidor ou bloqueador de chamadas: o executor de inferência ainda não está integrado a esses perfis. Não use o estado “habilitado” como prova de que há executor, contabilização de custo ou controle de cota operando. Essa integração deve aplicar limites antes de cada chamada, registrar consumo sem guardar conteúdo e falhar fechado quando não houver orçamento.

## Relação com o executor GitHub Actions

Esta configuração pertence ao runtime do Nivus. Ela não lê nem altera `GEMINI_API_KEY` do GitHub Actions. O executor de desenvolvimento do GitHub continua com segredos próprios, permissões próprias e aprovação humana; não copiar chaves entre esses dois ambientes.

## Rotas e validação

As rotas administrativas ficam em `backend/api/routers/ai_providers.py`; a cifra, validação de endpoint, teste explícito e auditoria ficam em `backend/services/ai_providers.py`. A migração é aditiva e cria as tabelas `ai_provider_connections` e `ai_provider_audit`.

A CI descobre `backend/test_ai_providers.py` com unittest. Os casos cobrem cifra e alteração de texto, autorização da política, orçamento obrigatório antes do teste de nuvem, limite de testes por hora, teste sem prompt, bloqueio de endereços privados em nuvem e loopback em endpoint local. A validação hospedada é necessária antes do merge; esta mudança não foi implantada no notebook.
