# Nivus Edge Node

O Nivus é um projeto aberto para construir uma plataforma de borda local-first, modular e de baixo consumo. Telemetria é um módulo da plataforma; sua agregação entre nós não é pré-requisito para o executor nem para a biblioteca compartilhada e será mais útil quando o Nó Master estiver operacional.

O alvo planejado é **Ubuntu Server minimal x86_64/amd64**. Isso ainda não significa compatibilidade comprovada com qualquer computador. O stack Compose está instalado em paralelo num notebook Ubuntu CCE U25. Em 21/11/2026, a release `2dfcbc0c2029723e44ff507857c72e7e8b83dfa3` foi aplicada com backup consistente; health HTTPS 200 e telemetria sem token 401 passaram. O navegador em largura móvel mostrou API online, telemetria recente e gráficos separados por unidade como padrão. A revisão foi em viewport móvel do navegador, não em Android físico. Consulte [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md); ainda faltam smoke entre dois dispositivos, instalação limpa, reboot, restauração e validação de outros hardwares.

## Estado do projeto

### Já funciona no notebook de teste

- API FastAPI separada em routers, schemas, dependências, segurança, banco e serviço MQTT.
- Login com senha e JWT, senha armazenada com PBKDF2, papéis de usuário e endpoints protegidos. No momento, o acesso é por senha; chave USB e biometria não estão implementadas.
- Painel React/Vite dividido em componentes, com login, telemetria, usuários e seções do dashboard.
- SQLite persistente, ingestão MQTT e agente de telemetria do host na instalação de teste. Telemetria agregada de vários nós é uma fase futura ligada ao Nó Master.
- Instalação Compose paralela com API, worker, Mosquitto e Nginx; HTTPS, backup e procedimento de rollback.
- Na atualização de 21/11/2026, a release `2dfcbc0c2029723e44ff507857c72e7e8b83dfa3` foi instalada pelo atualizador reversível; backup consistente, HTTPS 200 e telemetria sem token 401 foram confirmados. O painel carregou em viewport móvel com telemetria e gráficos separados por unidade. Reboot completo do Ubuntu e validação em Android físico ainda não foram confirmados.
- A interface servida mostra os avisos AGPL e links para o código e a licença.

### Planejado ou aguardando validação

- Registro seguro de nós integrado no PR #66. O agente mínimo está no PR #69 e passou CI hospedada (Ubuntu 22.04 amd64, testes isolados, Compose smoke e CodeQL); a validação em dois dispositivos reais continua pendente. Agregação de telemetria e painel multi-nó seguem pendentes.
- Home Assistant, Zigbee, sensores residenciais, medidores, câmeras, interfone e integração com inversor/baterias.
- Automação residencial real, VPN integrada ao produto e ações remotas em dispositivos.
- Inferência local, consulta à biblioteca de PDFs, fila de trabalhos entre máquinas e transferência P2P continuam planejadas. O cadastro administrativo de provedores está no PR #72; o executor de inferência runtime foi integrado no PR #82 e passou na CI hospedada em `main` (c0de53e). A release ativa `2dfcbc0c2029723e44ff507857c72e7e8b83dfa3` inclui esse executor, mas nenhuma chamada real a provedor foi feita. Isso é separado do executor GitHub Actions. Consulte [docs/AI_PROVIDER_CONNECTORS.md](docs/AI_PROVIDER_CONNECTORS.md).
- Modo de manutenção reversível na aba Configuração e CLI (`nivus maintenance enable|disable|status`), com `nivus help`, integrado no PR #28 e incluído na release ativa `2dfcbc0c2029723e44ff507857c72e7e8b83dfa3`. A CI passou; executar os comandos no notebook ainda está pendente.
- Configuração de sincronização NTP do Ubuntu, controle administrativo e rollback integrados nos PRs #40/#41 e presentes no update `fff64a68`; a release ativa `2dfcbc0c2029723e44ff507857c72e7e8b83dfa3` está implantada. Ainda falta validar visualmente os campos e o cadeado no notebook. Alterar NTP do host continua sendo ação explícita de administrador.
- Instalação limpa validada, reboot, atualização com rollback e matriz de hardware x86_64.
- O executor externo de desenvolvimento foi integrado no PR #3. Uma chamada autorizada para uma tarefa pública/sintética gerou o PR rascunho #16 e a CI passou. A abertura automática falhou naquela execução; a correção da leitura do branch padrão e a proteção contra propostas duplicadas foram integradas (PR #53). O fluxo completo ainda aguarda validação com uma nova chamada explicitamente autorizada; o PR #16 continua à espera de revisão humana. O notebook é suporte opcional; GitHub Actions é o executor principal.

Veja [docs/PROJECT_ROADMAP.md](docs/PROJECT_ROADMAP.md) para fases, entregáveis e critérios de conclusão; [docs/VISION.md](docs/VISION.md) registra a visão doméstica mais ampla. O estado verificado do notebook está em [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md).

O plano para evitar repetir a suíte completa em cada computador está em [docs/TEST_STRATEGY.md](docs/TEST_STRATEGY.md): CI em runners Ubuntu descartáveis hospedados pelo GitHub e uma matriz de seis plataformas físicas de referência (Intel e AMD, três faixas de geração) nos marcos de compatibilidade. Não é necessário instalar ou iniciar VMs no computador do operador.

Para orientar agentes de programação, dividir módulos e reutilizar conhecimento versionado, consulte [docs/AI_CONTEXT.md](docs/AI_CONTEXT.md), [docs/AI_WORKFLOW.md](docs/AI_WORKFLOW.md), [docs/AI_MODULE_WORKPLAN.md](docs/AI_MODULE_WORKPLAN.md), [docs/AI_EXECUTOR_IMPLEMENTATION.md](docs/AI_EXECUTOR_IMPLEMENTATION.md), [docs/AI_DEVELOPMENT_ORCHESTRATION.md](docs/AI_DEVELOPMENT_ORCHESTRATION.md) e o [índice de pesquisa dos vídeos](docs/VIDEO_RESEARCH_INDEX.md). A pasta `knowledge/` guarda notas públicas e índice lexical; `temp/` permanece fora do Git.

## Comece por aqui

Se você quer entender ou modificar o código:

1. Leia este README, [AGENTS.md](AGENTS.md), [CONTRIBUTING.md](CONTRIBUTING.md) e [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md).
2. Leia [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) e [docs/DECISIONS.md](docs/DECISIONS.md) antes de mudar limites entre módulos ou contratos de API.
3. Siga [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) para preparar backend, frontend e broker de desenvolvimento.
4. Escolha uma tarefa pequena com resultado verificável. Não trate itens da visão ou do roadmap como recursos já implementados.
5. Faça as verificações disponíveis para a área alterada, documente os resultados e atualize o estado/decisões se o comportamento mudou.

O roteiro de Ubuntu + Nivus instalado em USB foi integrado à `main` pelo PR #34 (`703efa4128f60460910b05ab344b60b082006a7e`); todos os checks hospedados passaram no head `3a1621dc11d2532853ef83b9ab5ea47f64cfaca5`. Consulte [deploy/portable_usb/README.md](deploy/portable_usb/README.md). Ainda faltam instalação, primeiro login, reboot e persistência em um USB físico; não é uma ISO customizada pronta nem uma versão de produção.

## Mapa do código

| Caminho | Responsabilidade |
| --- | --- |
| `backend/main.py` | Composição da aplicação FastAPI e inicialização |
| `backend/api/routers/` | Endpoints agrupados por domínio |
| `backend/api/schemas.py` | Contratos e validação de dados |
| `backend/api/dependencies.py` | Identidade e autorização das rotas |
| `backend/database.py` | SQLite, conexões e migrações aditivas |
| `backend/security.py` | Hash de senha, JWT e validações de segurança |
| `backend/services/` e `backend/mqtt_worker.py` | Serviços de domínio, manutenção reversível e processamento MQTT |
| `telemetry/agent.py` | Amostras de recursos do host e envio MQTT |
| `telemetry/hardware_sensors.py` | Classificação de temperaturas CPU/APU, placa-mãe e GPU |
| `telemetry/power_policy.py` | Fonte AC/NUT e governor CPUFreq opt-in, conservador por padrão |
| `frontend/src/components/` | Login e componentes visuais do dashboard |
| `deploy/` | Compose, Nginx, Mosquitto, instalador candidato, `nivus` CLI e operações |
| `deploy/portable_usb/` | Seleção explícita do USB, seed Subiquity privado e instalação pós-boot com dados persistentes |
| `docs/` | Visão, arquitetura, decisões, configuração, roadmap e status |
| `PROGRESS.html` | Página estática dos marcos; não lê a telemetria do host |

A semântica, origem e limites das leituras térmicas estão em [docs/HARDWARE_TELEMETRY.md](docs/HARDWARE_TELEMETRY.md).

## Instalação e execução

O desenvolvimento local está descrito em [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md). A instalação Compose para teste está em [deploy/README.md](deploy/README.md); ela requer Ubuntu, Docker/Compose, privilégios administrativos e credenciais iniciais criadas no terminal. A API e o broker ficam em redes privadas do Compose; MQTT não é publicado no host. Uma instalação nova publica a dashboard em HTTPS na porta 8443 por padrão e tenta a próxima porta livre se ela estiver ocupada; o instalador não altera o Nginx do host. No notebook de teste, o operador informou que a promoção reversível da issue #70 colocou o Compose em HTTPS 443 e preservou 8443 para retorno. O certificado autoassinado gera aviso no navegador.

Não há promessa de suporte a toda máquina x86_64 até validar Ubuntu minimal em instalações limpas e medir CPU, memória, armazenamento e periféricos. Veja os marcos pendentes antes de instalar fora do notebook de teste.

## Segurança e limites

- Não copie senhas, tokens, chaves, bancos, logs ou telemetria real para GitHub.
- Na LAN, prefira reservar um IP no roteador. Para acesso fora de casa, DDNS pode oferecer um nome estável, mas deve ser combinado com VPN; não encaminhe painel ou SSH diretamente à Internet.
- Comece integrações físicas em leitura e notificações. Um modelo de IA, reconhecimento facial ou leitura de placas não pode, sozinho, abrir portão, desarmar alarme ou desligar circuito crítico.
- Comandos MQTT precisam de identidade, tópicos permitidos, confirmação, timeout e intertravamentos locais.
- Câmeras, rostos, placas, áudio e presença exigem minimização, retenção limitada e controles de acesso.

Leia [docs/VISION.md](docs/VISION.md) para requisitos físicos, automações e limites de segurança. O Nivus não substitui detectores certificados nem projeto/instalação elétrica profissional.

## Licença

O Nivus é distribuído sob **AGPL-3.0-only**; consulte [LICENSE](LICENSE). Dependências e assets mantêm suas próprias licenças. O inventário está em [docs/THIRD_PARTY_LICENSES.md](docs/THIRD_PARTY_LICENSES.md). Preserve os avisos e o acesso ao código correspondente quando modificar ou executar a interface pela rede.
