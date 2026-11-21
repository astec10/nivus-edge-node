# Cadastro seguro de nós

**Estado:** API de registro integrada pelo PR #66 e presente no update `fff64a68` informado em 17/11; o último estado do notebook reportado depois é `f896de8`, sem sondagem nesta revisão. O agente mínimo foi implementado no [PR #69](https://github.com/astec10/nivus-edge-node/pull/69) e passou na CI hospedada. O smoke com dois dispositivos independentes ainda não foi executado.
**Issue:** [#65 concluída](https://github.com/astec10/nivus-edge-node/issues/65) pelo PR #66.
**Próxima validação:** smoke real com dois nós, incluindo TLS, reboot e revogação.

Este módulo estabelece identidade, pareamento, presença e revogação para os próximos passos multi-nó. A entrega inicial não agrega telemetria e não dá aos nós capacidade de executar ações uns nos outros.

## Limites da primeira entrega

Implementado e integrado no PR #66:

- Cadastro administrativo de um nó por código aleatório de uso único, expirado após 10 minutos.
- ID estável criado pelo servidor.
- Token aleatório de nó mostrado uma vez; apenas seu SHA-256 é persistido.
- Sessão rotativa para reduzir replay; renovar a sessão invalida a anterior.
- Heartbeat autenticado com sequência crescente, versão do agente, versão de esquema e capacidades permitidas.
- Horário de presença definido pelo servidor que recebeu a requisição.
- Estados `online`, `offline` e `revoked`; cadastro fica offline até o primeiro heartbeat.
- Listagem e revogação por administrador.

Fora do escopo:

- Enviar ou agregar amostras de telemetria.
- Controlar atuadores ou publicar comandos MQTT.
- Shell, execução remota de tarefas, cópia P2P ou atualização em massa.
- Descoberta por IP, hostname, número de série, User-Agent ou fingerprint de hardware.
- Autorização baseada nas capacidades declaradas.

## Agente mínimo de identidade e heartbeat (PR #69)

O candidato `node_agent/agent.py` contém um cliente de linha de comando sem dependências externas:

- `pair` recebe o código de uso único por prompt oculto e envia por HTTPS com validação de certificado ativa.
- O agente grava a credencial bearer em `~/.config/nivus-node-agent/credentials.json` (diretório `0700`, arquivo `0600`). O arquivo não é criptografado; proteja o disco e seus backups. O servidor continua guardando apenas o hash do token.
- `run` renova a sessão a cada inicialização e envia heartbeat a cada 30 segundos; falhas temporárias usam backoff limitado. Resposta perdida/replay provoca renovação da sessão; `401` encerra o agente.
- O payload inicial informa versão do agente/esquema e capacidades vazias. Não envia amostras, comandos, endereço IP ou hostname para autenticação.
- `deploy/nivus-node-agent.service.example` ilustra uma execução systemd com usuário dedicado sem root.

## Modelo de confiança

1. O administrador autenticado cria um pareamento. O código tem entropia alta, vale 10 minutos e só pode ser consumido uma vez.
2. O agente transmite o código por HTTPS. O servidor valida o hash, cria `node_id`, token e sessão e devolve os segredos uma única vez.
3. O agente armazena o token com permissões locais restritas. Ao iniciar/reiniciar, pede uma sessão nova; o token antigo continua sendo a credencial de identidade.
4. Cada heartbeat contém `session_id`, sequência, `agent_version`, `schema_version` e capacidades declaradas. Não aceita `node_id`, IP ou relógio do cliente como fonte de identidade/tempo.
5. A API compara token e sessão com os hashes persistidos, rejeita sequência repetida/antiga e atualiza `last_seen` com o horário do servidor.
6. O nó fica `online` se recebeu heartbeat há no máximo 90 segundos; agentes devem enviar a cada 30 segundos. Sem heartbeat recente fica `offline`.
7. O administrador pode revogar um nó. A revogação invalida token e sessão. Reentrada exige novo código de pareamento.

O token do nó é um segredo bearer. TLS é obrigatório em redes não confiáveis; não o inclua em logs, argumentos de linha de comando, screenshots ou repositório. Como a sessão é rotativa por nó, execute um agente ativo por identidade. Se o token se perder, revogue o nó e pareie-o novamente.

## Contrato HTTP candidato

Todos os caminhos abaixo usam o prefixo `/api/nodes`. Os exemplos são estruturais e usam placeholders; não cole códigos ou tokens reais em documentação.

### 1. Administrador cria código

```http
POST /api/nodes/enrollments
Authorization: Bearer <JWT_ADMIN>
```

Resposta: `enrollment_id`, `code`, `expires_at` e duração restante. Mostrar o campo `code` só na tela de pareamento; não registrar em log nem persistir no navegador. A rota exige papel administrador.

### 2. Nó consome o código

```http
POST /api/nodes/enroll
X-Nivus-Enrollment-Code: <CODIGO_DE_USO_UNICO>
Content-Type: application/json

{"name":"Edge Sala"}
```

Resposta única: `node_id`, `name`, `token`, `session_id`, intervalo sugerido e timeout. O nome aceita até 48 letras/dígitos Unicode (normalizados em NFC), espaços, ponto, hífen e sublinhado. O cliente não fornece ID, endereço, timestamp ou capacidade.

### 3. Nó renova a sessão

```http
POST /api/nodes/session
X-Nivus-Node-Token: <TOKEN_DO_NO>
```

Resposta: `node_id`, `session_id` novo e sequência inicial. A sessão anterior deixa de funcionar.

### 4. Nó envia heartbeat

```http
POST /api/nodes/heartbeat
X-Nivus-Node-Token: <TOKEN_DO_NO>
Content-Type: application/json

{
  "session_id":"<SESSAO_ATUAL>",
  "sequence":0,
  "agent_version":"1.0.0",
  "schema_version":1,
  "capabilities":["telemetry.cpu","telemetry.memory"]
}
```

Resposta `202`: estado aceito, ID do nó e horário de recebimento do servidor. Campos desconhecidos e capacidades fora da allowlist são rejeitados; heartbeat repetido ou fora de ordem recebe `409`.

### 5. Administrador lista e revoga

```http
GET /api/nodes
Authorization: Bearer <JWT_ADMIN>

DELETE /api/nodes/<NODE_ID>
Authorization: Bearer <JWT_ADMIN>
```

A listagem nunca retorna token, hashes, sessão ou códigos de pareamento. A rota de revogação só aceita nó ativo.

## Persistência e compatibilidade

`backend/database.py` cria tabelas aditivas `node_enrollments` e `nodes`; não altera as linhas antigas de telemetria nem reinterpreta o campo legado `telemetry.node`. Horários são armazenados em epoch UTC e devolvidos como ISO 8601 UTC. A tabela `nodes` não armazena endereço IP nem número de série.

A sequência crescente evita reuso e ordena requests dentro de uma sessão. Um reinício do agente pede nova sessão, que reinicia a sequência; não se deve executar dois agentes simultaneamente com o mesmo token.

## Validação e limites observados

Validação atual por PR #66, PR #69 e release do notebook:

1. [x] API: pareamento único/expiração, persistência hash-only, duas identidades, heartbeat/presença, replay, renovação e revogação.
2. [x] CI do PR #69: dois clientes, sessão por processo, recuperação de rede/resposta perdida, replay, permissões do arquivo de credenciais, HTTP recusado e revogação.
3. [x] CI hospedada aprovada para Ubuntu 22.04 amd64 Compose smoke, backend, frontend, CodeQL e índice de conhecimento.
4. [ ] Transporte simulado da CI não comprova uma conexão TLS de ponta a ponta; validar certificado e endpoints em execução.
5. [ ] Parear e executar dois agentes em dispositivos independentes, incluindo reboot e revogação.
6. [ ] Backup/restore com nós pareados precisa ser demonstrado operacionalmente.

A release `fff64a68f252f0b1290576e30b39ed78fbc15a7a` foi aplicada no notebook; sua saída confirmou build, backup consistente, restart, health HTTPS 200 e telemetria sem token 401. Isso não comprova reboot, smoke do agente ou painel multi-nó.

## Próximas entregas separadas

1. Executar smoke do agente em dois dispositivos reais; confirmar TLS, reboot e revogação.
2. Definir envelope de telemetria com timestamp de origem, unidade, qualidade, versão de esquema e timestamp de recepção.
3. Guardar dados por `node_id` sem quebrar consumidores do schema legado.
4. Criar visualização de nós com presença antiga claramente sinalizada e revogação administrativa.
5. Só após revisão separada, projetar atualização de artefatos assinados com canário e rollback por nó.
