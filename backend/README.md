# Backend Nivus — organização por domínio

## Entrada da API

O serviço atual continua iniciando com uvicorn main:app no diretório backend/. main.py compõe a aplicação, configura CORS, valida o segredo JWT no arranque, inicializa o SQLite e inclui os routers. Novas rotas não devem ser concentradas nele.

## Mapa de módulos

- api/dependencies.py: autenticação Bearer e autorização por papel.
- api/schemas.py: modelos de entrada da API.
- api/routers/auth.py: login e bloqueio por tentativas.
- api/routers/telemetry.py: telemetria e consulta de logs.
- api/routers/actuator.py: comando MQTT e auditoria.
- api/routers/alerts.py: histórico de alertas.
- api/routers/settings.py: leitura e alteração de limites.
- api/routers/users.py: administração de utilizadores e senhas.
- services/mqtt.py: publicação MQTT usada pela API.
- database.py: conexão, inicialização e migrações compatíveis do SQLite.
- security.py: hashes de senhas e tokens JWT.

## Limites de mudança

1. Coloque cada rota no router do seu domínio; use main.py somente para compor a aplicação.
2. Não altere paths, payloads, papéis, tópicos MQTT nem esquema SQLite sem atualizar a decisão e o plano de migração.
3. Não faça o coletor/worker abrir conexão de banco apenas por importar um módulo; use funções explícitas.
4. Não use a rede local como autorização administrativa.
5. Mudanças nesta cópia são candidatas até serem implantadas e verificadas no host; mantenha o serviço atual intacto até backup e rollback preparados.

A implantação systemd existente e a candidata modularizada usam os mesmos paths HTTP e o mesmo arquivo SQLite; o novo código ainda não foi ativado no notebook.
