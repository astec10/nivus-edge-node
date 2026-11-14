# Skills de apoio ao desenvolvimento Nivus

As skills são instruções reutilizáveis para o Codex. Elas ajudam a aplicar o contexto e os limites do projeto; não instalam módulos no Nivus, não alteram o roadmap e não substituem revisão humana.

As fontes destas skills ficam em codex-skills/ para revisão e distribuição pelo GitHub. A cópia instalada em ~/.codex/skills deve corresponder às fontes desse diretório. Skills de módulos futuros só descrevem como desenvolver a capacidade quando ela entrar no escopo; não são evidência de que a capacidade exista.

## Cobertura do objetivo e do roadmap

| Skill | Área | Fase do roadmap | Quando usar |
| --- | --- | --- | --- |
| nivus-project-guide | Contexto, limites e integração | Todas | Início de tarefa Nivus, revisão de estado ou mudança entre módulos |
| nivus-backend-api | FastAPI, segurança, SQLite e MQTT | 0, 2, 3 | Rotas, schemas, persistência, autenticação ou ingestão |
| nivus-dashboard-ui | React, acessibilidade e painéis | 0, 2 | Login, telemetria, navegação ou progresso |
| nivus-edge-operations | Compose, Ubuntu, backup e recuperação | 1 | Instalação, atualização, medição, reboot, backup ou rollback |
| nivus-hardware-telemetry | Sensores térmicos e de hardware do host | 1 | Identificar CPU/APU, placa-mãe, GPU e limites do driver |
| nivus-node-registry | Identidade, cadastro e heartbeat | 2 | Desenhar ou implementar monitoramento multi-nó autenticado |
| nivus-home-automation | Home Assistant, Zigbee, sensores e atuadores | 3 | Integrar dispositivos físicos e regras locais de segurança |
| nivus-local-ai-knowledge | PDFs, busca local e inferência | 4 | Organizar biblioteca, indexar fontes ou medir IA local |
| nivus-task-orchestration | Fila e execução de tarefas entre nós | 5 | Distribuir processamento com leases, limites e resultados verificáveis |
| nivus-ai-provider-connectors | Provedores externos, privacidade e quotas | 6 | Criar conectores comerciais opcionais |
| nivus-ai-dev-workflow | Orquestração externa de tarefas de desenvolvimento | Processo de contribuição; fora do runtime do Nivus | Planejar automação Discord/Jira/GitHub, roteamento de modelos e PRs com aprovação humana |

## Análise de aderência

O objetivo final depende primeiro de uma fundação que instala e se recupera sem perder dados. Por isso, a skill de operações cobre a fase imediata, enquanto backend e painel mantêm os contratos já existentes. A fase de identidade multi-nó vem antes da distribuição de tarefas; automação física e IA local têm skills próprias porque possuem riscos e critérios diferentes. Conectores comerciais ficam por último, depois de política de privacidade, orçamento e limites.

A divisão reduz conflito de edição: cada skill orienta uma fronteira funcional e a skill de projeto exige conferir dependências e estado antes de integrar. Não há uma skill separada para cada sensor, fabricante ou linguagem: esses conhecimentos ficam nas notas locais atômicas em temp/knowledge/ e nas referências oficiais, evitando inflar o conjunto instalado.

`nivus-hardware-telemetry` foi acrescentada porque a cobertura anterior não distinguia sensores genéricos ACPI de temperaturas de pacote/core. No CCE U25, isso fazia o painel gravar 29,8 °C de `acpitz` apesar do driver `coretemp` expor a temperatura real do pacote. A skill orienta como classificar leituras pelo driver/label, manter valores ausentes como N/A e validar cobertura sem inventar medições.

A skill `nivus-ai-dev-workflow` descreve uma ferramenta de produtividade para desenvolver o repositório. Ela não propõe instalar Hermes, OmniRoute, Jira ou Discord no computador de borda, nem altera as fases do produto. O fluxo requer integração e configuração explícitas; mantenha contas, quotas e termos dos provedores separados e preserve PR, CI e aprovação humana antes de produção.

## Instalação e manutenção

1. Revise a fonte da skill em codex-skills/<nome>/SKILL.md.
2. Valide frontmatter, nome e descrição. Mantenha descoberta automática; não defina invocação explícita sem pedido do operador.
3. Instale a pasta no diretório de skills do Codex.
4. Quando mudar a fonte, atualize a cópia instalada e confirme a próxima sessão do Codex.
5. Antes de publicar alterações no repositório, atualize este mapa se cobertura ou limites mudarem.
