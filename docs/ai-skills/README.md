# Skills portáteis do projeto Nivus

Este catálogo reúne, em arquivos separados, as orientações de trabalho por domínio do Nivus. Ele serve como contexto versionado para Codex e outros agentes; não é um pacote de plugins nem exige instalação na ferramenta de cada IA.

## Como atribuir uma tarefa

1. Leia [`../../AGENTS.md`](../../AGENTS.md), [`../AI_CONTEXT.md`](../AI_CONTEXT.md) e o estado atual em [`../PROJECT_STATUS.md`](../PROJECT_STATUS.md).
2. Escolha uma ou mais skills abaixo conforme o módulo da Issue. Não carregue o catálogo inteiro em toda tarefa.
3. Inclua os links das skills, as dependências, os arquivos permitidos, os critérios de aceite e o responsável humano na tarefa.
4. Trabalhe em branch/worktree isolada. Uma skill descreve limites e processo; não concede credenciais nem acesso a ferramentas.
5. Entregue diff/PR e evidências reais de validação para o integrador. Revisão humana continua necessária para merge e produção.

O coordenador pode manter o acesso ao GitHub e entregar ao worker apenas o contexto e o patch necessários. Cada provedor ainda precisa de autorização/configuração própria para executar o modelo. A Issue [`Trabalho paralelo de IA`](../../.github/ISSUE_TEMPLATE/parallel-ai-work-item.yml) é manual e não inicia automaticamente o executor existente.

## Skills

| Skill | Aplicar quando | Arquivo |
| --- | --- | --- |
| `nivus-project-guide` | Orientação inicial, estado do projeto, dependências ou trabalho entre módulos | [`SKILL.md`](nivus-project-guide/SKILL.md) |
| `nivus-backend-api` | Rotas FastAPI, schemas, autenticação, SQLite ou limites MQTT | [`SKILL.md`](nivus-backend-api/SKILL.md) |
| `nivus-node-registry` | Pareamento, identidade, heartbeat, presença ou telemetria multi-nó | [`SKILL.md`](nivus-node-registry/SKILL.md) |
| `nivus-hardware-telemetry` | Sensores de CPU/APU, placa, GPU, temperatura ou fontes térmicas | [`SKILL.md`](nivus-hardware-telemetry/SKILL.md) |
| `nivus-task-orchestration` | Fila de trabalho, leases, workers, cancelamento, isolamento ou artefatos | [`SKILL.md`](nivus-task-orchestration/SKILL.md) |
| `nivus-dashboard-ui` | React/Vite, login, dashboard, acessibilidade ou `PROGRESS.html` | [`SKILL.md`](nivus-dashboard-ui/SKILL.md) |
| `nivus-edge-operations` | Ubuntu, Docker Compose, systemd, backup/restore, deploy ou limites operacionais | [`SKILL.md`](nivus-edge-operations/SKILL.md) |
| `nivus-local-ai-knowledge` | IA local, RAG, biblioteca técnica, indexação ou inferência | [`SKILL.md`](nivus-local-ai-knowledge/SKILL.md) |
| `nivus-home-automation` | Home Assistant, Zigbee, sensores domésticos, energia, câmera ou atuadores | [`SKILL.md`](nivus-home-automation/SKILL.md) |
| `nivus-ai-provider-connectors` | APIs de provedores comerciais, dados enviados, segredos, quota ou custo | [`SKILL.md`](nivus-ai-provider-connectors/SKILL.md) |
| `nivus-ai-dev-workflow` | Coordenação de IAs de desenvolvimento, intake, modelos, branches, CI e PRs | [`SKILL.md`](nivus-ai-dev-workflow/SKILL.md) |

## Regra de manutenção

Estas playbooks são documentação do repositório e devem acompanhar mudanças nas fronteiras do módulo. Atualize a skill correspondente e o índice lexical com `python3 tools/build_ai_context.py`. Não descreva uma capacidade como implementada apenas porque aparece numa skill ou no roadmap; confirme o código e `PROJECT_STATUS.md`.

As skills de produto (`node-registry`, telemetria, orquestração, IA e automação) orientam o runtime Nivus. `nivus-ai-dev-workflow` trata apenas do desenvolvimento deste repositório e não deve ser instalado no nó de borda.
