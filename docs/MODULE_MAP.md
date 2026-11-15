# Mapa funcional e de dependências do Nivus

Este documento separa o que existe no código desta branch, o que foi observado no notebook e o que ainda é uma capacidade futura. Ele orienta onde uma mudança deve entrar e quais contratos precisam ser preservados. A presença de um diretório ou de uma skill não prova que uma função está integrada ou implantada.

## Árvore funcional

Nivus Edge Node
├── Nó de borda e interface
│   ├── Painel web: frontend/src — React/Vite, login e visualizações do nó
│   ├── Servidor web: deploy/nginx — TLS e proxy para a API
│   └── API: backend/main.py e backend/api
│       ├── routers — autenticação, usuários, telemetria, alertas, configurações e atuadores
│       ├── schemas.py — validação e contratos dos payloads
│       ├── dependencies.py — identidade, JWT e autorização por papel
│       ├── security.py — hash de senha e funções de segurança
│       ├── services/ — regras de integração, incluindo publicação MQTT
│       └── database.py — conexões SQLite e alterações aditivas de esquema
├── Coleta e mensageria
│   ├── telemetry/agent.py — amostras de recursos do host e sensores disponíveis
│   ├── Mosquitto — broker MQTT restrito às redes configuradas
│   └── backend/mqtt_worker.py — consumo de mensagens e persistência
├── Operação e recuperação
│   ├── docker-compose.yml — serviços, redes, limites e healthchecks
│   ├── deploy/ — instalação candidata, configuração, backup, restore e rollback
│   └── systemd do host — execução do agente leve de telemetria
├── Capacidades futuras do produto
│   ├── Registro e identidade de vários nós
│   ├── Home Assistant, Zigbee, sensores, energia, câmeras e interfone
│   ├── Base de conhecimento local e inferência local
│   ├── Fila de tarefas, distribuição de trabalho e transferência de artefatos
│   └── Conectores opcionais para provedores de IA comerciais
└── Apoio ao desenvolvimento
    ├── docs/ — decisões, arquitetura, status, roadmap e processo de IA
    ├── codex-skills/ — instruções para orientar tarefas por domínio
    └── temp/ — cache local opcional, ignorado pelo Git

## Fluxo de dependências atual

- Pessoa usuária → navegador → Nginx → arquivos estáticos do painel.
- Painel → Nginx → rotas FastAPI. A API valida o token e o papel antes da operação protegida.
- Routers FastAPI → schemas, dependências de autorização, serviços de domínio e camada SQLite.
- Agente do host → broker MQTT → worker → SQLite. O worker e a API usam a mesma base persistente da candidata.
- Serviço FastAPI → serviço MQTT → broker para comandos permitidos; a execução física exige confirmação e intertravamentos locais.
- Compose organiza API, worker, broker e Nginx. O agente de telemetria permanece como serviço do host e acessa o broker conforme a configuração protegida documentada em deploy/README.md.

O broker não deve ser publicado na LAN por conveniência. API, MQTT e banco têm fronteiras distintas; não crie uma dependência circular entre routers, serviços e acesso ao banco.

## Estado por capacidade

| Capacidade | Diretório ou contrato | Estado que pode ser afirmado |
| --- | --- | --- |
| Login por senha/JWT e papéis | backend/api, backend/security.py | Implementado; validação e operação no notebook estão descritas em PROJECT_STATUS.md. USB e biometria não estão implementadas. |
| Painel e telemetria de um nó | frontend/src, backend/api/routers | Implementados na candidata; painel e API foram observados no notebook. |
| Persistência e ingestão MQTT | backend/database.py, backend/mqtt_worker.py, telemetry/ | Implementadas; a stack Compose paralela foi observada coletando no notebook. |
| Backup, restore e rollback | deploy/ | Código e fluxo passaram CI descartável; teste em hardware físico e matriz multi-vendor continuam pendentes. O operador não usará VM local. |
| Catálogo autenticado de nós | Ainda sem módulo próprio | Planejado. Não há descoberta, cadastro ou revogação multi-nó integrados. |
| Automação doméstica e atuadores | Ainda sem adaptador Home Assistant completo | Planejado; proteções de segurança são requisito de projeto, não prova de integração. |
| Conhecimento e inferência local | Ainda sem runtime de RAG/inferência integrado | Planejado. O cache de desenvolvimento não é a biblioteca de conhecimento do produto. |
| Execução federada de tarefas | Ainda sem serviço de fila/leases | Planejado; não instalar agentes externos no nó de borda como substituto. |

## Caminho de uma mudança

1. Escolha um único domínio e leia a skill correspondente em docs/SKILL_MAP.md.
2. Localize o contrato: rota/schema, tabela, tópico MQTT, mensagem da UI ou configuração.
3. Faça a menor alteração que respeite o contrato e a fronteira do módulo.
4. Verifique a área tocada em ambiente descartável; não use o SQLite do notebook para testes.
5. Atualize PROJECT_STATUS.md, DECISIONS.md ou PROJECT_ROADMAP.md somente quando os fatos ou decisões mudarem.
6. Abra um PR pequeno, descrevendo evidências, limitações e rollback.

## Integrações futuras e dependências

- Home Assistant e Zigbee2MQTT devem entrar por um adaptador documentado, com credenciais próprias e modo inicial somente de leitura.
- Sensores de hardware devem usar as fontes do kernel Linux/hwmon e conservar nome, origem, unidade e validade da leitura.
- Câmeras e inferência visual devem emitir eventos com proveniência; reconhecimento de pessoa ou placa não pode ser a única autorização para um atuador.
- O registro de nós deve preceder distribuição de tarefas: identidade, autorização, revogação e heartbeat vêm antes da fila.
- A fila deve definir leases, limites de recurso, cancelamento, isolamento e verificação de artefatos antes de executar tarefas em outros computadores.
- Conectores comerciais devem ser opcionais, respeitar limites/custos e permitir fallback local; não são dependências do caminho básico do nó.

Veja PROJECT_ROADMAP.md para fases e critérios e ARCHITECTURE.md para detalhes da candidata atual.

## Desenvolvimento paralelo com IA (fora do runtime Nivus)

GitHub Issue revisada → controlador leve opcional no notebook → runner GitHub-hosted descartável → agente/modelo em sandbox → PR → CI → revisão humana. O intake de Issue existe; controlador no notebook, worker de código e provedores ainda não estão instalados. O fluxo não depende da telemetria nem do Nó Master. Leia AI_MODULE_WORKPLAN.md para dividir peças e serializar contratos compartilhados.
