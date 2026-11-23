# Cadastro seguro de nós

**Estado:** Cadastro/heartbeat (#66), lista read-only (#96), ingestão/histórico API (#97) e interface gráfica de histórico por nó (#99) estão integrados à `main`. Quatro workflows hospedados passaram após o merge #99 e novamente na `main` consultada. Smoke TLS em dois dispositivos, reboot, revogação e backup/restore físico continuam pendentes.
**Issue:** [#65 concluída](https://github.com/astec10/nivus-edge-node/issues/65) pelo PR #66.
**Próxima validação:** executar smoke com dois dispositivos independentes, incluindo TLS confiável, amostras no histórico gráfico, reboot, revogação e backup/restore.
**Situação do notebook (23/11):** checagem somente leitura via SSH confirmou a release `5a7ebd0b3e99895b4aa1c92461a0a89069cf6030`, serviço Compose ativo, health HTTPS local 200 e telemetria sem token 401. Portanto, PRs #96/#97/#99 estão instalados. Essa checagem não comprova reboot completo, TLS confiável ou operação com dois dispositivos físicos.

**Implementação do PR #97:** a branch integrou ao agente e à API amostras versionadas de CPU, memória e disco, além de contrato para outras métricas. A API retém e pagina dados por nó; o agente não executa comandos.

Este módulo estabelece identidade, pareamento, presença e revogação para os próximos passos multi-nó. A entrega inicial do PR #66 não agrega telemetria e não dá aos nós capacidade de executar ações uns nos outros. A ingestão autenticada e o histórico API por nó foram integrados pelo PR #97. A interface gráfica desse histórico foi integrada pelo PR #99; nós não executam ações uns nos outros.

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

Fora do escopo da primeira entrega do PR #66:

- Enviar ou agregar amostras de telemetria.
- Controlar atuadores ou publicar comandos MQTT.
- Shell, execução remota de tarefas, cópia P2P ou atualização em massa.
- Descoberta por IP, hostname, número de série, User-Agent ou fingerprint de hardware.
- Autorização baseada nas capacidades declaradas.

## Agente mínimo de identidade e heartbeat (PR #69)

A implementação inicial em `node_agent/agent.py` (PR #69) contém um cliente de linha de comando sem dependências externas:

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

## Envelope de telemetria multi-nó — PR #97 integrado

O endpoint candidato `POST /api/nodes/telemetry` aceita token de nó no cabeçalho `X-Nivus-Node-Token` e um corpo versionado:

```json
{
  "session_id": "<SESSAO_ATUAL>",
  "sequence": 1,
  "schema_version": 1,
  "observed_at": "2026-11-21T12:00:00Z",
  "samples": [
    {"metric": "cpu.utilization", "value": 23.5, "unit": "percent", "quality": "measured"},
    {"metric": "memory.utilization", "value": 48.0, "unit": "percent", "quality": "measured"},
    {"metric": "disk.utilization", "value": 61.0, "unit": "percent", "quality": "measured"}
  ]
}
```

- O contrato v1 permite `cpu.utilization`, `memory.utilization`, `disk.utilization`, `host_battery.level`, temperaturas identificadas e `power.estimated`, sempre com unidade, faixa, qualidade e número limitado de amostras. O agente inicial coleta somente CPU, memória e disco; os demais permanecem indisponíveis até integrações específicas.
- Qualidades aceitas: `measured`, `estimated` e `unavailable`. Leitura indisponível exige `value: null`; NaN, infinito, booleanos, unidade incorreta, métrica desconhecida, duplicatas e campos adicionais são rejeitados.
- A sequência é compartilhada com heartbeat. O agente envia heartbeat e depois telemetria com sequência crescente; o servidor serializa a validação SQLite sob transação. Repetição exata da mesma sessão, sequência e conteúdo retorna aceite idempotente. Conteúdo divergente ou sequência antiga sem lote correspondente retorna `409`.
- O servidor aceita no máximo um lote novo a cada 30 segundos por nó, inclusive após renovar a sessão. Repetições idênticas continuam idempotentes e não consomem intervalo; uma tentativa antecipada recebe `429` com `Retry-After`. Na implementação do agente PR #97, o agente mantém a cadência configurada de heartbeat e envia telemetria respeitando o intervalo mínimo de 30 segundos entre novos lotes.
- `observed_at` registra o relógio UTC informado pelo nó; `received_at` e `last_seen` vêm do servidor. O histórico administrativo devolve ambos e o desvio em segundos; relógio do cliente não decide presença.
- Os dados ficam em `node_telemetry_batches` e `node_telemetry_samples`, associados ao `node_id`, com chaves estrangeiras e remoção de lotes e amostras vencidos após 14 dias tanto na ingestão quanto na consulta do histórico, inclusive para nó offline. Isso é aditivo e não altera `telemetry.node` nem o histórico legado.
- A rota proposta para histórico é `GET /api/nodes/{node_id}/telemetry`, exclusiva para administrador, limitada a 500 lotes por consulta (cada lote pode conter até 32 métricas) e ordenada cronologicamente dentro de cada página. `limit` aceita de 1 a 500; `offset` é limitado a 40.320 e o cliente reutiliza o `snapshot_until` ISO 8601 emitido na resposta. Metadados de total, offset, limite, mais páginas, faixa e snapshot são expostos por cabeçalhos HTTP; o corpo permanece uma lista JSON para compatibilidade.
- O agente só declara capacidades de CPU/memória/disco quando `/proc` está disponível. Usa amostras de `/proc/stat`, `/proc/meminfo` e uso do filesystem raiz; primeira leitura de CPU e fontes inválidas ficam explicitamente indisponíveis. Temperatura, bateria e energia não são inferidas por este coletor.

O PR #97 foi integrado à `main` após quatro workflows hospedados aprovados: Dashboard/sensores, Ubuntu 22.04, CodeQL e índice. Os testes cobrem paginação por 14 dias, lacunas, picos nas bordas, expiração offline, snapshot estável e rejeição de offset inválido. Isso valida software no runner, não a coleta real de sensores, transporte TLS entre dispositivos ou armazenamento numa instalação do usuário. A resposta de aceite confirma armazenamento no Nó Master, não validade física do sensor nem uma ação de automação.

## Histórico paginado — Issue #103 concluída

A issue #103 foi encerrada após revisão do código de #97/#99. A consulta mantém páginas limitadas a 500 lotes e informa total, faixa, snapshot e cobertura; a interface distingue janela selecionada, lotes brutos, página e pontos exibidos, sem agregar amostras. Testes sintéticos de 14 dias cobrem lacuna, nó offline, expiração e picos nas bordas. Não é necessário abrir uma nova tarefa de runtime para esses critérios.

A CI valida esses comportamentos com dados sintéticos; TLS, dois dispositivos físicos, reboot, revogação e backup/restore operacional permanecem validações separadas.

## Validação e limites observados

Evidências disponíveis para PRs integrados:

1. [x] API inicial: pareamento único/expiração, persistência hash-only, duas identidades, heartbeat/presença, replay, renovação e revogação.
2. [x] CI do PR #69: dois clientes, sessão por processo, recuperação de rede/resposta perdida, replay, permissões do arquivo de credenciais, HTTP recusado e revogação.
3. [x] CI hospedada do PR #97 após a correção do cursor ISO 8601: Dashboard and hardware telemetry, Ubuntu VM validation, CodeQL e Knowledge index — todos concluídos com sucesso.
4. [ ] A validação em runner hospedado não comprova conexão TLS entre dispositivos reais; validar certificado e endpoints em execução.
5. [ ] Parear e executar dois agentes em dispositivos independentes, incluindo reboot e revogação.
6. [ ] Backup/restore com nós pareados precisa ser demonstrado operacionalmente.

**Histórico de implantação relatado:** em 23/11, a release ativa `5a7ebd0b3e99895b4aa1c92461a0a89069cf6030` e o health local foram confirmados por SSH; PRs #96/#97/#99 estão implantados. A sequência de testes físicos ainda está pendente.

## Próximas entregas separadas

1. PR #99 integrou o histórico gráfico da issue #98; validar ausência, atraso, relógio divergente, erros e paginação no painel, sem enviar comandos remotos.
2. Parear e executar dois agentes em dispositivos independentes; confirmar TLS confiável, coleta, reboot, revogação e backup/restore com dados de nós.
4. Só após revisão separada, projetar atualização de artefatos assinados com canário e rollback por nó.
