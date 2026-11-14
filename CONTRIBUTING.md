# Como contribuir

Obrigado por ajudar no Nivus. O projeto está em desenvolvimento: diferencie recursos ativos, candidatos de teste e ideias futuras antes de propor mudanças.

## 1. Leia a documentação na ordem

1. [`README.md`](README.md): resumo, estado e mapa de código.
2. [`AGENTS.md`](AGENTS.md): regras de segurança e colaboração para agentes e pessoas.
3. [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md): o que foi realmente verificado no notebook.
4. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) e [`docs/DECISIONS.md`](docs/DECISIONS.md): fronteiras entre módulos e decisões em vigor.
5. [`docs/PROJECT_ROADMAP.md`](docs/PROJECT_ROADMAP.md): objetivos, fases e critérios de conclusão.
6. [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md): ambiente e comandos de desenvolvimento.
7. Para mudanças de instalação/serviços, [`deploy/README.md`](deploy/README.md) e [`docs/VM_VALIDATION.md`](docs/VM_VALIDATION.md): teste em instalação Ubuntu isolada e limites atuais de backup/restore.

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

Preserve rotas, payloads, nomes de variáveis e comportamento existente durante refatorações, a menos que a mudança inclua uma migração e documentação explícitas. Não misture uma extração estrutural com uma reformulação visual ou de produto.

## 3. Prepare um ambiente isolado

- Siga `docs/DEVELOPMENT.md` para Python, Node e broker MQTT.
- Use uma cópia/branch de trabalho, banco descartável, segredos locais e portas livres.
- Nunca conecte testes à base SQLite de produção nem reutilize chaves ou senhas reais.
- Para testar Compose, configure os caminhos de dados e secrets para uma pasta temporária. Leia `deploy/README.md` antes de executar `deploy/verify-compose-staging.sh`: esse script remove arquivos de segredo da sua pasta de staging e deve rodar somente numa cópia isolada.
- `deploy/install.sh` é um instalador candidato com privilégios de root. Não o execute num host com dados importantes; prefira uma VM Ubuntu descartável e faça snapshot antes.
- `deploy/restore.sh` altera a base SQLite. Execute `--check` antes de qualquer uso e faça restauração real apenas num clone descartável da VM; nunca valide restore sobre a instalação ativa do notebook.
- `deploy/test-restore-rollback.sh` injeta de propósito uma falha de health depois de trocar a base. Rode somente dentro de uma VM descartável após snapshot; exige duas confirmações e cria um backup de segurança antes de iniciar.

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
- Hardware: declare modelo, versão do Ubuntu, arquitetura, memória e driver/label dos sensores. Não classifique zona ACPI genérica como CPU; sensor ausente ou ambíguo permanece nulo e aparece como N/D. Consulte [docs/HARDWARE_TELEMETRY.md](docs/HARDWARE_TELEMETRY.md). Uma validação no CCE U25 não prova suporte a qualquer computador x86_64.

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
