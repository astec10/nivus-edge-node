# Arquitetura da candidata

Esta árvore descreve somente a candidata local em staging.

## Backend

- backend/main.py compõe a aplicação FastAPI e inclui routers.
- backend/api/routers/ contém autenticação, telemetria, atuadores, alertas, configurações e usuários.
- backend/api/schemas.py define os payloads de entrada.
- backend/api/dependencies.py valida JWT e papel do usuário.
- backend/database.py mantém SQLite e inicialização/migração aditiva.
- backend/security.py contém hashing PBKDF2 e helpers JWT.
- backend/services/mqtt.py publica comandos; backend/mqtt_worker.py persiste eventos.

## Coleta e frontend

- telemetry/agent.py coleta métricas locais e publica MQTT.
- frontend/src/App.jsx compõe os componentes de frontend/src/components/.
- O frontend é o painel recuperado modularizado; login estilo roteador e dashboard multi-nó permanecem requisitos futuros.

## Segurança e execução

SQLite fica em caminho configurável. Segredo JWT deve ser externo ao repositório. CORS não concede origens por padrão. Broker MQTT e redes precisam de credenciais e segmentação. O Compose é uma candidata isolada: API e worker compartilham uma imagem Python, Mosquitto fica em rede privada sem porta MQTT publicada, Nginx não privilegiado publica HTTPS pela rede `edge_ingress`, API e broker permanecem em redes internas, e o agente leve de telemetria executa como serviço systemd no host. Um helper root resolve o IP atual do broker antes de cada início e grava apenas o endpoint em `/run`; a senha MQTT continua como credencial systemd para o usuário sem privilégios. O instalador candidato usa caminhos próprios e não substitui systemd/Nginx existentes. A primeira instalação no notebook passou health/HTTPS/401, mas revelou falha de conexão do coletor, que está em correção; ainda não houve validação limpa independente.

O worker MQTT persiste telemetria no mesmo SQLite da API; os serviços possuem limites de CPU/memória configuráveis e logs limitados. O agente reporta estimativa de potência, não medição física. Temperatura pode não estar disponível.
