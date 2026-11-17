# Cadastro seguro de nós

**Estado:** primeira implementação em branch, ainda não integrada nem instalada.  
**Issue:** [#65](https://github.com/astec10/nivus-edge-node/issues/65)  
**Branch:** `feat/node-registry-bootstrap-20261117`

Este módulo estabelece identidade, pareamento, presença e revogação para os próximos passos multi-nó. A entrega inicial não agrega telemetria e não dá aos nós capacidade de executar ações uns nos outros.

## Limites da primeira entrega

Incluído na candidata:

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

## Validação prevista

Antes de tratar o módulo como pronto:

1. CI executa testes isolados SQLite para pareamento único, expiração, hashes, duas identidades, heartbeat e presença, replay, renovação e revogação.
2. Smoke HTTP confirma autorização administrativa e códigos 401/403/409/422 para os casos relevantes.
3. Dois agentes simulados aparecem separadamente; parar um os torna offline sem afetar o outro.
4. Revogar um impede a sessão e os heartbeats seguintes.
5. Backup/restore preserva o schema e o estado do registro.

A CI é validação de software. A proposta não está na release do notebook e ainda não há agente Nivus de pareamento nem painel multi-nó.

## Próximas entregas separadas

1. Integrar/validar o contrato do registro e adicionar cliente/agente mínimo de pareamento.
2. Definir envelope de telemetria com timestamp de origem, unidade, qualidade, versão de esquema e timestamp de recepção.
3. Guardar dados por `node_id` sem quebrar consumidores do schema legado.
4. Criar visualização de nós com presença antiga claramente sinalizada e revogação administrativa.
5. Só após revisão separada, projetar atualização de artefatos assinados com canário e rollback por nó.
