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
  Routers --> Schemas[backend/api/schemas.py]
  Routers --> Auth[backend/api/dependencies.py + security.py]
  Routers --> DB
  API --> MQTT
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
| `backend/services/` | chamadas internas ↔ serviços | MQTT, logs e operações de domínio; não expõe portas diretamente. |
| `backend/database.py` | conexões ↔ SQLite | Persistência, migrações aditivas e consultas. |
| `backend/mqtt_worker.py` | MQTT → validação/persistência | Consome telemetria e registra alertas de regra determinística. |
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
Issue ai:ready
  → worker/modelo em GitHub Actions hospedado
  → branch de proposta → CI hospedada → PR em rascunho → revisão humana
branch padrão após merge + despacho manual do mantenedor
  → runner auxiliar opcional no notebook
  → testes Python, sintaxe e build do frontend no Ubuntu físico
```

O executor de IA e a CI de PR usam runners hospedados; a fila continua no GitHub se o notebook estiver desligado. O runner auxiliar do notebook é opt-in e só valida a branch padrão após merge. Ele não executa Issues, modelos, PRs/forks, Compose ou deploy e não recebe segredos nem Docker. O fluxo de instalação e remoção fica em deploy/notebook-support/README.md. Hermes/OmniRoute/Discord/Jira são opções de ferramentas externas, não serviços do nó Nivus. O executor não depende do agente de telemetria nem do Nó Master. Ver [AI_DEVELOPMENT_ORCHESTRATION.md](AI_DEVELOPMENT_ORCHESTRATION.md).
## Scheduler Nivus entre nós (futuro)

```text
identidade de nó → inventário de capacidade → fila/lease → worker isolado
                → artefato com checksum → validação/aceite → auditoria
```

Esse scheduler não está implementado. A Fase 2 fornece cadastro/heartbeat e a Fase 5 define leases, idempotência, quotas, cancelamento e recuperação. Compartilhar um arquivo ou GPU pela LAN não agrega RAM/VRAM por si só.
