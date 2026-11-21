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

## Perfil de desempenho por AC/UPS (opt-in)

O controlador opcional em `telemetry/power_policy.py` muda somente o governor CPUFreq. O exemplo `deploy/power-policy.json.example` vem com `enabled: false`; não ative até verificar os nomes de governor suportados em todas as políticas CPUFreq (`scaling_available_governors`). O perfil `on_ac` usa o governor escolhido para desempenho e `conservative` é usado quando a fonte retorna bateria, falha, fica ausente ou ambígua. `performance`, `userspace` e `balance_performance` não podem ser declarados conservadores. O controlador verifica o governor conservador e, em AC, usa o governor de desempenho apenas se estiver listado por todas as políticas; caso contrário, mantém o perfil conservador. Se o governor conservador não for suportado, a execução falha antes de qualquer escrita e o governor corrente permanece como está. O kernel mantém seus limites térmicos. Atuadores e overclock ficam fora desta política.

Escolha a fonte conforme a ligação elétrica:

- `linux_mains` com `feed_topology: direct_ac` só quando a fonte Mains do Linux representa um adaptador ligado diretamente à rede elétrica. Se o computador recebe energia da saída de um UPS, use `feed_topology: ups_output`; essa combinação sempre seleciona o perfil conservador, pois não revela o estado da entrada do UPS.
- Para entrada de linha do UPS, configure NUT localmente e escolha `source: { "type": "nut", "target": "nome-configurado@localhost" }`. Nivus não instala NUT. O cliente `upsc` é de leitura e a fonte precisa ser local. Resposta ausente, inválida ou stale resulta no perfil conservador.

Para ativar manualmente no host, primeiro revise o arquivo e marque `enabled` como `true`, confirme a fonte/topologia e os governors disponíveis. Depois instale as unidades opcionais e habilite o timer:

    sudo install -o root -g root -m 0600 deploy/power-policy.json.example /etc/nivus-compose/power-policy.json
    sudoedit /etc/nivus-compose/power-policy.json
    sudo install -o root -g root -m 0644 deploy/nivus-performance-policy.service /etc/systemd/system/
    sudo install -o root -g root -m 0644 deploy/nivus-performance-policy.timer /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now nivus-performance-policy.timer

O timer reconcilia a cada 30 segundos. Veja `systemctl status nivus-performance-policy.timer` e `journalctl -u nivus-performance-policy.service`. A unidade roda como root, com escrita de sysfs limitada à árvore `/sys/devices/system/cpu/cpufreq`; ela precisa dessa permissão para alterar o governor. Para desativar com retorno ao perfil conservador: edite `enabled` para `false`, execute `sudo systemctl start nivus-performance-policy.service` e depois `sudo systemctl disable --now nivus-performance-policy.timer`. Enquanto a configuração existir com `enabled: false`, a execução aplica somente o governor conservador e não lê a fonte de energia. Não apague o arquivo antes desse retorno: removê-lo impede novas execuções, mas mantém o governor que já estava aplicado. Não ative esse perfil até validar o governor e a fonte de energia no computador específico.


Para a candidata Compose, consulte `deploy/README.md` e `.env.example`. Não reutilize o banco do notebook nem segredos de produção numa instalação de teste.


## Hora do host

A preferência de fuso, hora e data altera apenas a apresentação no navegador. Para configurar a hora do Ubuntu, a API fornece \`GET /api/settings/time-sync\` a usuários autenticados e limita \`POST /api/settings/time-sync\` e \`POST /api/settings/time-sync/rollback\` a administradores.

O controlador raiz opera somente sobre \`/etc/systemd/timesyncd.conf.d/90-nivus.conf\`. Ele só aplica mudanças se \`systemd-timesyncd.service\` já estiver ativo e nenhum outro cliente NTP listado estiver ativo. Ele não instala nem substitui clientes. Os nomes DNS são validados na API e novamente no controlador privilegiado; URLs, portas, endereços IP e fontes repetidas são recusados. A lista padrão é \`a.ntp.br\`, \`b.ntp.br\`, \`c.ntp.br\`, três servidores do mesmo projeto NTP.br. O systemd-timesyncd usa as fontes disponíveis sequencialmente; não há quorum.

Antes de cada mudança o controlador salva a configuração Nivus anterior em \`/var/backups/nivus-compose/time-sync\`. Em falha no reinício ele tenta restaurar a configuração e o índice de backup. O endpoint de rollback restaura a configuração Nivus anterior. O serviço API acessa o controlador por \`/run/nivus-time-sync/control.sock\`, montado como somente leitura no container e autorizado por credenciais Unix do peer; não há \`sudo\` geral nem comandos arbitrários.
