# Nivus Edge Node

O Nivus é um projeto aberto para construir uma plataforma de borda local-first, modular e de baixo consumo. Telemetria é um módulo da plataforma; sua agregação entre nós não é pré-requisito para o executor nem para a biblioteca compartilhada e será mais útil quando o Nó Master estiver operacional.

O alvo planejado é **Ubuntu Server minimal x86_64/amd64**. Isso ainda não significa compatibilidade comprovada com qualquer computador. O stack Compose está instalado em paralelo num único notebook Ubuntu CCE U25; a release `fff64a68f252f0b1290576e30b39ed78fbc15a7a` foi aplicada em 17/11/2026. O registro seguro de nós está na release (PR #66); o agente mínimo de pareamento e heartbeat foi implementado no PR #69 e passou na CI hospedada. Ainda faltam smoke real entre dois dispositivos, instalação limpa, reboot, restauração e validação de outros hardwares.

## Estado do projeto

### Já funciona no notebook de teste

- API FastAPI separada em routers, schemas, dependências, segurança, banco e serviço MQTT.
- Login com senha e JWT, senha armazenada com PBKDF2, papéis de usuário e endpoints protegidos. No momento, o acesso é por senha; chave USB e biometria não estão implementadas.
- Painel React/Vite dividido em componentes, com login, telemetria, usuários e seções do dashboard.
- SQLite persistente, ingestão MQTT e agente de telemetria do host na instalação de teste. Telemetria agregada de vários nós é uma fase futura ligada ao Nó Master.
- Instalação Compose paralela com API, worker, Mosquitto e Nginx; HTTPS, backup e procedimento de rollback.
- A instalação Compose paralela passou health HTTPS, HTTP 401 sem token e login; a última atualização reconstruiu e reiniciou os containers, criou backup SQLite consistente e confirmou health 200/401. A instalação antiga systemd/Nginx continua separada e ativa. Na release atual, a nova dashboard atende HTTPS 8443; a promoção da nova interface para a porta 443 ainda está pendente (issue #70).
- A interface servida mostra os avisos AGPL e links para o código e a licença.

### Planejado ou aguardando validação

- Registro seguro de nós integrado no PR #66. O agente mínimo está no PR #69 e passou CI hospedada (Ubuntu 22.04 amd64, testes isolados, Compose smoke e CodeQL); a validação em dois dispositivos reais continua pendente. Agregação de telemetria e painel multi-nó seguem pendentes.
- Home Assistant, Zigbee, sensores residenciais, medidores, câmeras, interfone e integração com inversor/baterias.
- Automação residencial real, VPN integrada ao produto e ações remotas em dispositivos.
- Inferência local, consulta à biblioteca de PDFs, fila de trabalhos entre máquinas, transferência P2P e conectores para provedores comerciais com limites de uso. A gestão de perfis de API para o runtime está especificada na issue #68; não é a mesma credencial do executor GitHub Actions.
- Modo de manutenção reversível na aba Configuração e CLI (`nivus maintenance enable|disable|status`), com `nivus help`, integrado no PR #28 e incluído na release atual. A CI passou; execução operacional dos comandos no notebook ainda pendente.
- Configuração de sincronização NTP do Ubuntu, controle administrativo e rollback integrados nos PRs #40/#41 e incluídos na release atual; ainda falta validar visualmente os campos e o cadeado no notebook. Alterar NTP do host continua sendo ação explícita de administrador.
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
| `frontend/src/components/` | Login e componentes visuais do dashboard |
| `deploy/` | Compose, Nginx, Mosquitto, instalador candidato, `nivus` CLI e operações |
| `deploy/portable_usb/` | Seleção explícita do USB, seed Subiquity privado e instalação pós-boot com dados persistentes |
| `docs/` | Visão, arquitetura, decisões, configuração, roadmap e status |
| `PROGRESS.html` | Página estática dos marcos; não lê a telemetria do host |

A semântica, origem e limites das leituras térmicas estão em [docs/HARDWARE_TELEMETRY.md](docs/HARDWARE_TELEMETRY.md).

## Instalação e execução

O desenvolvimento local está descrito em [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md). A instalação Compose para teste está em [deploy/README.md](deploy/README.md); ela requer Ubuntu, Docker/Compose, privilégios administrativos e credenciais iniciais criadas no terminal. A API e o broker ficam em redes privadas do Compose; MQTT não é publicado no host. O instalador publica a dashboard em HTTPS na porta 8443 por padrão e tenta a próxima porta livre se ela estiver ocupada; ele não altera o Nginx do host nem promove o Compose para 443. Acessar sem sufixo de porta em instalação existente é acompanhado pela issue #70. O certificado autoassinado gera aviso no navegador.

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
