# Arquitetura da candidata

Esta árvore descreve a implementação versionada do Nivus. Cadastro inicial, lista administrativa read-only, ingestão/histórico API e UI de histórico por nó foram integrados pelos PRs #66, #96, #97 e #99. Quatro workflows hospedados passaram após o merge #99 e novamente na `main` consultada; a CI não comprova TLS ou operação em dispositivos reais. O notebook permanece na release `2dfcbc0c2029723e44ff507857c72e7e8b83dfa3`, sem evidência de implantação dos PRs #96/#97/#99.

A issue #103 de cobertura do histórico foi encerrada: paginação limitada, metadados de cobertura, amostras preservadas sem agregação e testes sintéticos de 14 dias já fazem parte do código integrado. Temperatura e bateria interna por nó seguem planejadas na issue #102, com a cadeia #112 (contrato v2 com origem) → #113 (coleta Linux) → #114 (visão por nó e unidades separadas).

## Backend

- backend/main.py compõe a aplicação FastAPI e inclui routers.
- backend/api/routers/ contém autenticação, telemetria, atuadores, bateria móvel, alertas, configurações, usuários e `nodes.py`. `mobile_battery.py` separa cadastro administrativo de relatórios autenticados por token do celular. `nodes.py` contém rotas administrativas de pareamento/listagem/revogação e endpoints de agente para cadastro, sessão e heartbeat; o PR #97 acrescenta ingestão de envelopes e histórico protegido.
- backend/api/schemas.py define os payloads de entrada.
- backend/api/dependencies.py valida JWT e papel do usuário.
- backend/database.py mantém SQLite e inicialização/migração aditiva.
- backend/api/routers/ai_providers.py (issue #68) oferece CRUD administrativo; backend/services/ai_providers.py cifra chaves com AES-GCM usando chave externa, faz validação de rede e teste GET sem prompts. A rota não habilita um executor de inferência.
- backend/services/maintenance.py compartilha o estado volátil do modo de manutenção, registra transições no SQLite e volta ao modo normal após reboot.
- `backend/services/nodes.py` implementa o contrato de identidade multi-nó integrado no PR #66: código de pareamento de uso único, token armazenado como hash, sessão rotativa, sequência contra replay e presença derivada do heartbeat do servidor.
- `backend/services/node_telemetry.py` no PR #97 valida métricas, sessão, replay/idempotência e limite de um lote novo a cada 30 segundos. Retém 14 dias e remove lotes expirados também ao consultar o histórico, mesmo para nó offline. O histórico é admin-only, limitado a 500 lotes por página, usa offset limitado e snapshot ISO 8601 estável. Os quatro workflows hospedados passaram; o código está integrado, mas ainda não foi implantado no notebook.
- `node_agent/agent.py` (PR #69) é um cliente stdlib para pareamento HTTPS e heartbeat. O PR #97 estende `node_agent/telemetry.py` para coletar somente CPU, memória e disco do Linux, preservar a sequência do heartbeat e marcar fontes ausentes como indisponíveis. Não executa comandos; a CI hospedada passou, mas ainda falta smoke TLS real entre dispositivos.
- backend/security.py contém hashing PBKDF2 e helpers JWT.
- `backend/services/mobile_battery.py` aplica frescor, limiar de 20%, latch por ciclo e publica somente `OFF` no tópico fixo permitido; o broker não confirma o estado físico.
- backend/services/mqtt.py publica comandos; backend/mqtt_worker.py persiste eventos.

## Coleta e frontend

- telemetry/agent.py coleta métricas locais e publica MQTT.
- deploy/nivusctl fornece comandos allowlisted `maintenance enable|disable|status` e `help`; o marcador compartilhado fica em `/run/nivus-maintenance`, não em dados persistentes.
- frontend/src/App.jsx compõe os componentes de frontend/src/components/.
- O frontend é o painel recuperado modularizado; login estilo roteador e dashboard multi-nó permanecem requisitos futuros.

## Segurança e execução

SQLite fica em caminho configurável. Segredo JWT deve ser externo ao repositório. CORS não concede origens por padrão. Broker MQTT e redes precisam de credenciais e segmentação. O Compose é uma candidata isolada: API e worker compartilham uma imagem Python, Mosquitto fica em rede privada sem porta MQTT publicada, Nginx não privilegiado publica HTTPS pela rede `edge_ingress`, API e broker permanecem em redes internas, e o agente leve de telemetria executa como serviço systemd no host. Um helper root resolve o IP atual do broker antes de cada início e grava apenas o endpoint em `/run`; a senha MQTT continua como credencial systemd para o usuário sem privilégios. O instalador candidato usa caminhos próprios e não substitui systemd/Nginx existentes. A primeira instalação real passou health/HTTPS/401, mas revelou falha de conexão do coletor; o reparo foi aplicado e a contagem SQLite aumentou de 9 para 12 em 15 segundos. Ainda falta validação limpa independente.

O worker MQTT persiste telemetria no mesmo SQLite da API; os serviços possuem limites de CPU/memória configuráveis e logs limitados. No modo de manutenção, o agente continua iniciado, mas pausa leitura/publicação; o worker continua iniciado e descarta mensagens novas antes de gravá-las. API, autenticação, painel, health e broker permanecem ativos. Um comando `disable` retoma a operação sem reboot; como o marcador fica em `/run`, reiniciar o Ubuntu também retorna ao modo normal. O agente reporta estimativa de potência, não medição física. Temperatura pode não estar disponível.

## Gestão de provedores

A issue #68 adiciona configuração administrativa sem acoplar o backend aos jobs do GitHub Actions. O PR #72 foi incluído na release `f896de8` aplicada ao notebook. O executor runtime da issue #74 foi integrado pelo PR #82; `backend/api/routers/ai_executor.py` expõe execução/cancelamento/auditoria administrativos e `backend/services/ai_executor.py` valida política, reserva orçamento e chama somente o provedor escolhido. A chave é descriptografada apenas em memória; prompts/respostas não são persistidos; não há fallback, retry ou execução do resultado. CI hospedada passou, nenhuma chamada real foi feita e a implantação do #82 no notebook não foi confirmada. Consulte [AI_PROVIDER_CONNECTORS.md](AI_PROVIDER_CONNECTORS.md).

- `telemetry/power_policy.py` lê alimentação via Linux power_supply ou NUT local, seleciona somente governadores listados em CPUFreq e permanece conservador diante de falha/ambiguidade. `deploy/nivus-performance-policy.service` e `.timer` são opt-in e executam fora do container. A unidade root tem escrita restrita à árvore CPUFreq; não muda limites de frequência/tensão, proteções térmicas, atuadores ou overclock. O candidato ainda aguarda CI, revisão e habilitação física.
