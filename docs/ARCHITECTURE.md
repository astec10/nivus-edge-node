# Arquitetura da candidata

Esta árvore descreve a implementação versionada do Nivus. O primeiro cadastro de nós está em uma branch de desenvolvimento e ainda não pertence à release ativa do notebook.

## Backend

- backend/main.py compõe a aplicação FastAPI e inclui routers.
- backend/api/routers/ contém autenticação, telemetria, atuadores, bateria móvel, alertas, configurações, usuários e a proposta `nodes.py`. `mobile_battery.py` separa cadastro administrativo de relatórios autenticados por token do celular. `nodes.py` contém rotas administrativas de pareamento/listagem/revogação e endpoints de agente para cadastro, sessão e heartbeat.
- backend/api/schemas.py define os payloads de entrada.
- backend/api/dependencies.py valida JWT e papel do usuário.
- backend/database.py mantém SQLite e inicialização/migração aditiva.
- backend/services/maintenance.py compartilha o estado volátil do modo de manutenção, registra transições no SQLite e volta ao modo normal após reboot.
- `backend/services/nodes.py` implementa o primeiro contrato de identidade multi-nó em branch: código de pareamento de uso único, token armazenado como hash, sessão rotativa, sequência contra replay e presença derivada de heartbeat do servidor. Essa proposta não inclui coleta/agregação, execução remota ou atualizações de frota.
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
