# Configuração

A API e o worker aceitam `NIVUS_MQTT_PASSWORD_FILE` para buscar credenciais em arquivo montado; o agente host também aceita esse formato via credenciais do systemd. O instalador Docker candidato gera credenciais fora do repositório.

Variáveis lidas pela API: NIVUS_DB_PATH, NIVUS_JWT_SECRET_FILE, NIVUS_CORS_ORIGINS, NIVUS_NODE_NAME, NIVUS_MQTT_BROKER, NIVUS_MQTT_PORT, NIVUS_MQTT_USERNAME, NIVUS_MQTT_PASSWORD, NIVUS_MQTT_ALLOWED_TOPICS, NIVUS_TELEMETRY_TOPIC e NIVUS_MAINTENANCE_STATE_PATH. Compose configura o caminho do estado da API/worker a partir de NIVUS_MAINTENANCE_STATE_DIR; para desenvolvimento, use `./runtime-state`. O instalador cria `/run/nivus-maintenance` com permissões para os serviços e apaga o marcador no reboot.

Comandos de manutenção (`nivus maintenance enable|disable|status`) são instalados junto com o Nivus. `status` é somente leitura; mudanças exigem `sudo`. Use `nivus help` para a lista resumida e `nivus help maintenance` para detalhes. A API guarda o estado de auditoria em `maintenance_audit`; o marcador ativo fica somente em `/run`, então o reboot é um retorno automático ao modo normal.

Gere o segredo JWT fora do repositório e restrinja leitura ao usuário de serviço. Não use .env versionado nem copie credenciais ou banco real para desenvolvimento.

Exemplo Linux para gerar um novo segredo em diretório pessoal:

    install -d -m 700 ~/.config/nivus-edge
    umask 077
    python3 -c 'import secrets; print(secrets.token_hex(48))' > ~/.config/nivus-edge/jwt_secret
    chmod 600 ~/.config/nivus-edge/jwt_secret

Configure valores de MQTT conforme broker local. O arquivo .env.example contém nomes e defaults demonstrativos, não credenciais utilizáveis.


Para a candidata Compose, consulte `deploy/README.md` e `.env.example`. Não reutilize o banco do notebook nem segredos de produção numa instalação de teste.
