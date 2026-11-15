# Como contribuir

Obrigado por ajudar no Nivus. O projeto está em desenvolvimento: diferencie recursos ativos, candidatos de teste e ideias futuras antes de propor mudanças.

## 1. Leia a documentação na ordem

1. [`README.md`](README.md): objetivo, estado e instalação.
2. [`AGENTS.md`](AGENTS.md): limites de segurança e colaboração.
3. [`docs/AI_CONTEXT.md`](docs/AI_CONTEXT.md): contexto estável e fontes canônicas.
4. [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md): evidências datadas, estado e pendências.
5. [`docs/MODULE_MAP.md`](docs/MODULE_MAP.md): árvore funcional, dependências e estado dos módulos.
6. [`docs/SKILL_MAP.md`](docs/SKILL_MAP.md): skills disponíveis e cobertura do roadmap.
7. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) e [`docs/DECISIONS.md`](docs/DECISIONS.md): fronteiras e decisões vigentes.
8. [`docs/PROJECT_ROADMAP.md`](docs/PROJECT_ROADMAP.md): objetivos, fases e critérios de conclusão.
9. [`docs/AI_WORKFLOW.md`](docs/AI_WORKFLOW.md): fontes comuns, biblioteca versionada e passagem entre sessões.
10. [`docs/AI_MODULE_WORKPLAN.md`](docs/AI_MODULE_WORKPLAN.md) e [`docs/AI_EXECUTOR_IMPLEMENTATION.md`](docs/AI_EXECUTOR_IMPLEMENTATION.md): peças paralelas, limites e estado do executor.
11. [`docs/VIDEO_RESEARCH_INDEX.md`](docs/VIDEO_RESEARCH_INDEX.md) e [`knowledge/README.md`](knowledge/README.md): fontes, resumos e índice compartilhado.
12. [`docs/OPEN_SOURCE_COMPONENTS.md`](docs/OPEN_SOURCE_COMPONENTS.md): componentes pesquisados, candidatos e limites.
13. [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md): ambiente e comandos de desenvolvimento.
14. Para instalação/serviços, [`deploy/README.md`](deploy/README.md) e [`docs/VM_VALIDATION.md`](docs/VM_VALIDATION.md): ambiente isolado e limites de backup/restore.

Se os documentos discordarem, confirme o código e o status atuais. Corrija a documentação junto com a mudança; não transforme uma ideia do roadmap em uma afirmação de que a função já existe.

## 2. Escolha uma mudança pequena

Antes de editar, descreva o problema em poucas linhas, o comportamento esperado e como será verificado. Trabalhe numa área por vez:

- API, validação e autorização: `backend/api/`.
- SQLite e alterações de esquema: `backend/database.py`.
- MQTT e persistência de mensagens: `backend/services/` e `backend/mqtt_worker.py`.
- Métricas do host: `telemetry/`.
- Interface: `frontend/src/`.
- Instalação, redes, serviços e backup: `deploy/`.
- Objetivos e decisões: `docs/`.

Escolha a fronteira pelo [mapa de módulos](docs/MODULE_MAP.md). Em trabalho paralelo, mantenha PRs separados por função e coordene antes de editar arquivos compartilhados (`backend/main.py`, `backend/api/schemas.py`, `backend/database.py`, `docker-compose.yml` e ACL MQTT). Integre primeiro o contrato e depois as implementações dependentes; evite dependências circulares.

Preserve rotas, payloads, nomes de variáveis e comportamento existente durante refatorações, a menos que a mudança inclua uma migração e documentação explícitas. Não misture uma extração estrutural com uma reformulação visual ou de produto.

## 3. Prepare um ambiente isolado

- Siga `docs/DEVELOPMENT.md` para Python, Node e broker MQTT.
- Use uma cópia/branch de trabalho, banco descartável, segredos locais e portas livres; para VMs, use somente CI hospedada, nunca o computador pessoal do operador.
- Nunca conecte testes à base SQLite de produção nem reutilize chaves ou senhas reais.
- Para testar Compose, configure os caminhos de dados e secrets para uma pasta temporária. Leia `deploy/README.md` antes de executar `deploy/verify-compose-staging.sh`: esse script remove arquivos de segredo da sua pasta de staging e deve rodar somente numa cópia isolada.
- `deploy/install.sh` é um instalador candidato com privilégios de root. Não o execute num host com dados importantes; prefira runner Ubuntu descartável hospedado pelo GitHub; não inicie VMs no computador do operador.
- `deploy/restore.sh` altera a base SQLite. Execute `--check` antes de qualquer uso e faça restauração real apenas num runner ou sandbox descartável hospedado; nunca valide restore sobre a instalação ativa do notebook.
- `deploy/test-restore-rollback.sh` injeta de propósito uma falha de health depois de trocar a base. Rode somente em runner descartável hospedado pelo CI; exige duas confirmações e cria um backup de segurança antes de iniciar.

## 4. Implemente na fronteira correta

- Mantenha cada rota curta: validação no schema, autorização em dependência, acesso a dados em serviço/repositório e regra de negócio em módulo próprio.
- Configure segredos por arquivos ou variáveis documentadas. Não fixe senhas, IPs privados, caminhos de computador ou tokens no código.
- Para banco, prefira migrações aditivas. Escreva primeiro o plano de backup/rollback e não apague nem renomeie colunas usadas por versões existentes sem transição compatível.
- Para novos serviços, documente finalidade, porta, rede, volume persistente, usuário, limites de CPU/memória, healthcheck, logs e como parar/recuperar.
- Para alterações no MQTT, preserve autenticação, ACL e allowlist de tópicos. Não exponha o broker à LAN por conveniência.
- Para UI, preserve acessibilidade, uso em telas pequenas e o link/aviso AGPL. Prefira componentes pequenos e não acrescente dependências sem necessidade.

## 5. Valide o que mudou

Use as ferramentas disponíveis na área alterada e informe exatamente o que executou. O repositório ainda não possui uma suíte completa de testes automatizados; um build ou smoke test não prova toda a segurança nem compatibilidade de hardware.

- Backend: compile/importação e smoke test com SQLite temporário; valide autorização com e sem token.
- Frontend: `npm ci` e `npm run build` dentro de `frontend/`; confira o login, assets e avisos de licença.
- Compose: `docker compose config --quiet`, build e o smoke test isolado descrito em `deploy/README.md`.
- Segurança: confira que rotas sensíveis exigem autenticação e papel correto; não imprima senhas, JWTs, cookies, `.env` ou conteúdo de banco nos logs.
- Persistência: confirme que o banco e a configuração sobrevivem a recriação do container; documente backup, restauração e rollback.
- Hardware: declare modelo, versão do Ubuntu, arquitetura, memória, portas e periféricos testados. Uma validação no CCE U25 não prova suporte a qualquer computador x86_64.

Não declare testes, build, deploy ou validação que não tenha executado. Se algo não pôde ser testado, registre como pendente.

## 6. Atualize a documentação e abra a contribuição

Antes de enviar:

1. Atualize `docs/PROJECT_STATUS.md` para separar feito, staging, pendente e futuro.
2. Registre decisões duradouras em `docs/DECISIONS.md` e variáveis novas em `docs/CONFIGURATION.md`.
3. Atualize `docs/PROJECT_ROADMAP.md` somente se o objetivo, fase ou critério mudar.
4. Revise `git diff` e verifique `.env`, bancos, logs, screenshots e arquivos de chave.
5. Inclua uma descrição curta com problema, solução, arquivos/módulos afetados, verificações executadas, riscos conhecidos e rollback.
6. Liste dependências novas e suas licenças. Preserve `AGPL-3.0-only` para o Nivus e notices de terceiros.

### Lista de revisão

- [ ] A mudança resolve um objetivo declarado e tem escopo claro.
- [ ] Os contratos existentes continuam compatíveis ou há uma migração documentada.
- [ ] Segredos, dados pessoais e endereços privados não foram incluídos.
- [ ] A validação corresponde ao alcance da afirmação feita.
- [ ] Estado, configuração, licenças e rollback foram documentados.
- [ ] Recursos de automação física não dependem apenas de uma previsão de IA.

Não envie temp/ nem arquivos locais de contexto. O padrão do repositório ignora /temp/; confirme esse estado antes de adicionar arquivos. Decisões duradouras devem ser registradas nos documentos oficiais. O cache descrito em AI_WORKFLOW.md não é um recurso do runtime.

Para uma tarefa de código, selecione uma skill funcional de docs/SKILL_MAP.md quando ela melhorar o resultado. Skills não substituem a leitura do estado e do código atual.

## 7. Automação de manutenção no GitHub

O repositório acompanha atualizações semanais por Dependabot para Python, npm, imagens Docker, Docker Compose e GitHub Actions. Cada atualização chega como PR e precisa passar pela CI e pela revisão de uma pessoa; não habilite merge automático para dependências sem avaliar impacto e compatibilidade.

O workflow CodeQL procura padrões de vulnerabilidade em Python, JavaScript/TypeScript e GitHub Actions em PRs, commits na `main` e uma agenda semanal. Um resultado limpo reduz riscos conhecidos, mas não prova segurança completa.

Use docs/OPEN_SOURCE_COMPONENTS.md antes de propor ferramenta ou API de terceiros; registrar licença, manutenção, recursos e plano de remoção. Use os formulários de issue para descrever problema, módulo, critérios de aceite e evidência sanitizada. Use o modelo de PR para registrar escopo, validações reais, dados afetados e rollback. Esses recursos organizam contribuições e tarefas de IA; não instalam serviços no host Nivus nem substituem revisão humana.


## Biblioteca compartilhada e executor

Mantenha notas públicas e curadas em `knowledge/catalog/` e `knowledge/topics/`, com fonte, licença e estado de verificação. Gere o índice com `python3 tools/build_ai_context.py`. Não publique dados reais do notebook. Leia `docs/AI_MODULE_WORKPLAN.md` antes de delegar peças; contratos compartilhados precisam de um integrador. O intake de tarefas não chama modelos nem concede autorização para merge.
