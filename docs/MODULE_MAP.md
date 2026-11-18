# Mapa de módulos e dependências

Este mapa distingue o que existe do que está planejado. Os caminhos são relativos à raiz do repositório.

## Nó de borda atual

```mermaid
flowchart TD
  Host[Ubuntu host] --> Agent[telemetry/agent.py]
  Agent --> MQTT[Mosquitto MQTT]
  MQTT --> Worker[backend/mqtt_worker.py]
  Worker --> DB[(SQLite persistente)]
  Browser[Browser] --> Nginx[Nginx HTTPS]
  Nginx --> UI[frontend React/Vite]
  UI --> API[backend/main.py FastAPI]
  API --> Routers[backend/api/routers]
  Phone[Home Assistant Companion App] -->|HTTPS + token por dispositivo| Nginx
  Routers --> BatteryRouter[backend/api/routers/mobile_battery.py]
  BatteryRouter --> BatteryService[backend/services/mobile_battery.py]
  BatteryService --> DB
  BatteryService --> MQTT
  Admin[Administrador] -->|JWT admin| NodesRouter[backend/api/routers/nodes.py]
  NodeAgent[node_agent/agent.py] -->|HTTPS + token do nó| NodesRouter
  NodesRouter --> NodesService[backend/services/nodes.py]
  NodesService --> DB
  Routers --> Schemas[backend/api/schemas.py]
  Routers --> Auth[backend/api/dependencies.py + security.py]
  Routers --> DB
  AIExecutor[api/routers/ai_executor.py] -->|admin + explicit task| Inference[services/ai_executor.py]
  Inference --> ProviderProfiles[services/ai_providers.py]
  Inference --> ExecutorLedger[(ai_execution_tasks + ai_execution_requests)]
  Inference --> SelectedProvider[Selected provider only]
  API --> MQTT
  Operator[Admin dashboard or CLI] --> Maintenance[backend/services/maintenance.py]
  Maintenance --> State[/run maintenance marker/]
  Maintenance --> DB
  Agent[telemetry/agent.py] --> State
  Worker[backend/mqtt_worker.py] --> State
  Compose[docker-compose.yml] --> Nginx
  Compose --> API
  Compose --> Worker
  Compose --> MQTT
```

### Fronteiras

| Módulo | Entrada/saída | Responsabilidade |
| --- | --- | --- |
| `telemetry/` | métricas do host → MQTT | Coleta CPU, memória, disco, energia estimada e sensores disponíveis; não implementa a política da API. |
| `backend/api/routers/` | HTTP autenticado ↔ schemas | Endpoints por domínio; exige autorização nas rotas sensíveis. |
| `backend/api/routers/mobile_battery.py` | Admin JWT + relatório tokenizado | Admin cadastra/revoga; celular envia somente percentual e horário. O cliente não escolhe tópico nem comando. |
| `backend/api/routers/nodes.py` | Admin JWT ou credencial própria do nó | Pareamento one-use, sessão, heartbeat ordenado, listagem e revogação; a candidata atual não executa operações remotas. |
| `backend/services/nodes.py` | Contratos validados ↔ SQLite | Cria IDs no servidor, persiste somente hashes de códigos/tokens, deriva estado pelo heartbeat e restringe capacidades a uma allowlist; integrado pelo PR #66. |
| `node_agent/agent.py` | CLI pareamento/run ↔ API de nós | Cliente stdlib candidato no PR #69: código oculto de uso único, TLS obrigatório, token local `0600`/diretório `0700`, sessão renovável e heartbeat apenas com metadados. Sem telemetria, comandos ou ações remotas; smoke físico pendente. |
| `backend/services/mobile_battery.py` | Leitura móvel validada → regra + auditoria MQTT | Rejeita leituras antigas/repetidas; publica somente `OFF` em `nivus/edge/relay1` a ≤20%; recuperação acima de 20% rearma sem enviar `ON`. |
| `backend/services/` | chamadas internas ↔ serviços | MQTT, logs e operações de domínio; não expõe portas diretamente. |
| `backend/api/routers/ai_executor.py` + `backend/services/ai_executor.py` | tarefa explícita → provedor selecionado | Execução administrativa única, com classe de dados, orçamento, timeout, cancelamento e auditoria mínima; sem retry, fallback ou execução do resultado. Issue #74 ainda em revisão. |
| `backend/database.py` | conexões ↔ SQLite | Persistência, migrações aditivas e consultas. |
| `backend/mqtt_worker.py` | MQTT → validação/persistência | Consome telemetria e registra alertas de regra determinística. |
| `backend/services/maintenance.py` | Admin API/CLI → estado volátil + audit SQLite | Alterna coleta em background com allowlist; o marcador desaparece no reboot. |
| `deploy/nivusctl` | terminal → maintenance service | Expõe `nivus help` e ações `maintenance enable|disable|status`; escrita exige sudo. |
| `frontend/src/` | API ↔ componentes React | Login e dashboard; não decide segurança de backend. |
| `deploy/` e `docker-compose.yml` | arquivos de configuração → processos | Instalação, redes, volumes, health, backup e rollback. |

Consulte [`ARCHITECTURE.md`](ARCHITECTURE.md), [`PROJECT_STATUS.md`](PROJECT_STATUS.md) e os arquivos de cada módulo antes de mudar contratos. O mapa não substitui o código.

## Biblioteca compartilhada futura

```mermaid
flowchart LR
  Sources[Fontes com licença/proveniência] --> Extract[Extração/OCR/legenda autorizada]
  Extract --> Review[Revisão e estado de evidência]
  Review --> Chunks[Notas atomizadas por tema]
  Chunks --> Lexical[Índice lexical reproduzível]
  Lexical --> Retrieval[Consulta com citações]
  Identity[Identidade e ACL por nó] --> Retrieval
  Retrieval --> Agents[Agentes locais autorizados]
```

`knowledge/catalog/` e `knowledge/topics/` são conteúdo público curado. Extração, indexação lexical executável, consulta na aplicação e replicação autenticada em vários nós ainda são trabalho da Fase 4.

## Paralelismo externo de desenvolvimento (fora do runtime)

```text
GitHub Issue aprovada (ai:ready)
  → intake GitHub Actions valida escopo e autorização
  → runner efêmero GitHub-hosted executa modelo e worker limitado
  → draft PR → CI → revisão humana → merge/deploy
```

O intake GitHub Issues/Actions, a chamada de modelo autorizada e o worker limitado executado em runner GitHub-hosted existem. Uma chamada para a issue pública/sintética #6 criou o draft #16; a abertura automática falhou naquela execução por ausência de checkout. O commit `bec9573` corrigiu a leitura da branch padrão pela API, e o PR #53 adicionou proteção contra propostas duplicadas, limpeza dos rótulos da fila e comentário com o link do draft. Ainda não houve nova chamada autorizada para confirmar o ciclo automático após essas correções; o PR #16 continua draft e exige revisão humana. O worker não faz merge nem deploy.

O PR #18 propõe um runner opcional no notebook para checks confiáveis da branch principal, mas continua draft, não está integrado nem instalado e não substitui os runners hospedados. Não há controlador persistente no notebook nem integração ativa com Discord, Jira, Hermes ou OmniRoute. Este executor de desenvolvimento não depende da telemetria local ou do Nó Master. Ver [`AI_MODULE_WORKPLAN.md`](AI_MODULE_WORKPLAN.md), [`AI_EXECUTOR_IMPLEMENTATION.md`](AI_EXECUTOR_IMPLEMENTATION.md) e [`AI_DEVELOPMENT_ORCHESTRATION.md`](AI_DEVELOPMENT_ORCHESTRATION.md).

## Scheduler Nivus entre nós (futuro)

```text
identidade de nó → inventário de capacidade → fila/lease → worker isolado
                → artefato com checksum → validação/aceite → auditoria
```

Esse scheduler não está implementado. A Fase 2 fornece cadastro/heartbeat e a Fase 5 define leases, idempotência, quotas, cancelamento e recuperação. Compartilhar um arquivo ou GPU pela LAN não agrega RAM/VRAM por si só.

O executor runtime da issue #74 é separado do dispatcher GitHub Actions e do futuro scheduler distribuído. Ele opera em uma solicitação administrativa explícita para o provedor selecionado; não distribui tarefas entre nós.
