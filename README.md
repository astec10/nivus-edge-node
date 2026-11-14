# Nivus Edge Node

O Nivus é um projeto aberto para construir uma plataforma de borda local-first: primeiro coleta e organiza telemetria com segurança num computador Linux de baixo consumo; depois poderá integrar automação residencial, vários nós e processamento local ou distribuído.

O alvo planejado é **Ubuntu Server minimal x86_64/amd64**. Isso ainda não significa compatibilidade comprovada com qualquer computador. Até agora, o stack Compose foi instalado e operado em paralelo num único notebook Ubuntu CCE U25. Uma instalação limpa independente, reboot, restauração e mais modelos de hardware ainda precisam de validação.

## Estado do projeto

### Já funciona no notebook de teste

- API FastAPI separada em routers, schemas, dependências, segurança, banco e serviço MQTT.
- Login com senha e JWT, senha armazenada com PBKDF2, papéis de usuário e endpoints protegidos. No momento, o acesso é por senha; chave USB e biometria não estão implementadas.
- Painel React/Vite dividido em componentes, com login, telemetria, usuários e seções do dashboard.
- SQLite persistente, ingestão MQTT e agente de telemetria do host.
- Instalação Compose paralela com API, worker, Mosquitto e Nginx; HTTPS, backup e procedimento de rollback.
- A candidata Compose passou health HTTPS, HTTP 401 sem token e login; o coletor publica telemetria continuamente. A instalação antiga systemd/Nginx continua separada e ativa.
- A interface servida mostra os avisos AGPL e links para o código e a licença.

### Ainda é plano

- Descoberta, cadastro e telemetria de vários nós numa única tela.
- Home Assistant, Zigbee, sensores residenciais, medidores, câmeras, interfone e integração com inversor/baterias.
- Automação residencial real, VPN integrada ao produto e ações remotas em dispositivos.
- Inferência local, consulta à biblioteca de PDFs, fila de trabalhos entre máquinas, transferência P2P e conectores para provedores comerciais com limites de uso.
- Instalação limpa validada, reboot, atualização com rollback e matriz de hardware x86_64.

Veja [docs/PROJECT_ROADMAP.md](docs/PROJECT_ROADMAP.md) para fases, entregáveis e critérios de conclusão; [docs/VISION.md](docs/VISION.md) registra a visão doméstica mais ampla. O estado verificado está em [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md). O [mapa funcional e de dependências](docs/MODULE_MAP.md) separa módulos existentes e planejados; [docs/AI_CONTEXT.md](docs/AI_CONTEXT.md) e [docs/AI_WORKFLOW.md](docs/AI_WORKFLOW.md) orientam sessões de IA e a passagem de contexto. A cobertura das skills está em [docs/SKILL_MAP.md](docs/SKILL_MAP.md).

O plano para não repetir a suíte completa em cada computador está em [docs/TEST_STRATEGY.md](docs/TEST_STRATEGY.md): CI numa VM Ubuntu limpa para cada alteração e uma matriz de seis plataformas físicas de referência (Intel e AMD, três faixas de geração) nos marcos de compatibilidade.

Para reutilizar contexto e consultas técnicas de programação entre sessões, veja [docs/AI_WORKFLOW.md](docs/AI_WORKFLOW.md). O cache opcional em temp/ é local e ignorado pelo Git; este repositório ainda não inclui um gerador executável. Atomização significa dividir notas por conceito, e a busca lexical normaliza termos — isso não equivale à tokenização interna de um modelo. Decisões permanentes devem ficar nos documentos canônicos.

## Comece por aqui

Se você quer entender ou modificar o código:

1. Leia este README, [AGENTS.md](AGENTS.md), [CONTRIBUTING.md](CONTRIBUTING.md), [docs/AI_CONTEXT.md](docs/AI_CONTEXT.md) e [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md).
2. Leia [docs/MODULE_MAP.md](docs/MODULE_MAP.md), [docs/SKILL_MAP.md](docs/SKILL_MAP.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) e [docs/DECISIONS.md](docs/DECISIONS.md) antes de mudar limites entre módulos ou contratos de API.
3. Siga [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) para preparar backend, frontend e broker de desenvolvimento.
4. Escolha uma tarefa pequena com resultado verificável. Não trate itens da visão ou do roadmap como recursos já implementados.
5. Faça as verificações disponíveis para a área alterada, documente os resultados e atualize o estado/decisões se o comportamento mudou.

O roteiro detalhado para contribuições está em [CONTRIBUTING.md](CONTRIBUTING.md). Consulte o [catálogo de componentes open source](docs/OPEN_SOURCE_COMPONENTS.md) para opções pesquisadas, estado de adoção e impactos; os itens listados são candidatos e não foram instalados. O pacote de instalação é candidato, não uma versão de produção: siga [deploy/README.md](deploy/README.md) e o [roteiro da VM Ubuntu limpa](docs/VM_VALIDATION.md); não use uma máquina com dados importantes como ambiente de teste.

## Mapa do código

| Caminho | Responsabilidade |
| --- | --- |
| `backend/main.py` | Composição da aplicação FastAPI e inicialização |
| `backend/api/routers/` | Endpoints agrupados por domínio |
| `backend/api/schemas.py` | Contratos e validação de dados |
| `backend/api/dependencies.py` | Identidade e autorização das rotas |
| `backend/database.py` | SQLite, conexões e migrações aditivas |
| `backend/security.py` | Hash de senha, JWT e validações de segurança |
| `backend/services/` e `backend/mqtt_worker.py` | Publicação MQTT e processamento de eventos |
| `telemetry/agent.py` | Amostras de recursos do host e envio MQTT |
| `frontend/src/components/` | Login e componentes visuais do dashboard |
| `deploy/` | Compose, Nginx, Mosquitto, instalador candidato e operações |
| `docs/` | Visão, arquitetura, decisões, configuração, roadmap e status |
| `PROGRESS.html` | Página estática dos marcos; não lê a telemetria do host |

## Instalação e execução

O desenvolvimento local está descrito em [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md). A instalação Compose para teste está em [deploy/README.md](deploy/README.md); ela requer Ubuntu, Docker/Compose, privilégios administrativos e credenciais iniciais criadas no terminal. A API e o broker ficam em redes privadas do Compose; MQTT não é publicado no host. O painel HTTPS usa certificado autoassinado por padrão.

Não há promessa de suporte a toda máquina x86_64 até validar Ubuntu minimal em instalações limpas e medir CPU, memória, armazenamento e periféricos. Veja os marcos pendentes antes de instalar fora do notebook de teste.

## Segurança e limites

- Não copie senhas, tokens, chaves, bancos, logs ou telemetria real para GitHub.
- Acesso remoto de administração deve usar rede privada/VPN e regras restritas; não encaminhe painel ou SSH diretamente à Internet.
- Comece integrações físicas em leitura e notificações. Um modelo de IA, reconhecimento facial ou leitura de placas não pode, sozinho, abrir portão, desarmar alarme ou desligar circuito crítico.
- Comandos MQTT precisam de identidade, tópicos permitidos, confirmação, timeout e intertravamentos locais.
- Câmeras, rostos, placas, áudio e presença exigem minimização, retenção limitada e controles de acesso.

Leia [docs/VISION.md](docs/VISION.md) para requisitos físicos, automações e limites de segurança. O Nivus não substitui detectores certificados nem projeto/instalação elétrica profissional.

## Manutenção do repositório

O GitHub acompanha versões semanais de dependências e executa CodeQL no código. Issues e pull requests usam modelos que pedem módulo, escopo, critérios de aceite, evidências e rollback. Veja [CONTRIBUTING.md](CONTRIBUTING.md) antes de propor uma mudança. Dependabot abre propostas; uma pessoa deve revisar e aprovar cada atualização.

## Licença

O Nivus é distribuído sob **AGPL-3.0-only**; consulte [LICENSE](LICENSE). Dependências e assets mantêm suas próprias licenças. O inventário está em [docs/THIRD_PARTY_LICENSES.md](docs/THIRD_PARTY_LICENSES.md). Preserve os avisos e o acesso ao código correspondente quando modificar ou executar a interface pela rede.
