# Contexto estável para agentes de IA

Atualizado: 2026-11-14. Este arquivo é um ponto de orientação, não um snapshot automático. Antes de afirmar o estado atual, consulte os links abaixo e a branch/PR em questão.

## Objetivo

Construir uma plataforma local-first de nó de borda que começa monitorando um host Linux x86_64 de baixo consumo e pode crescer, por módulos independentes, para vários nós, automação doméstica segura, conhecimento e inferência local e distribuição controlada de tarefas. O alvo é Ubuntu Server minimal amd64. Compatibilidade universal ainda não foi comprovada.

## Estado conhecido e limites

- A base atual contém uma API FastAPI, painel React, SQLite, MQTT, agente de telemetria e implantação candidata Compose.
- A instalação systemd/Nginx antiga e a candidata Compose são ambientes separados no notebook de teste. Verifique PROJECT_STATUS.md antes de citar o estado ao vivo.
- O login atualmente usa senha e JWT. USB, Face ID e leitor biométrico não são recursos implementados.
- Multi-nó, Home Assistant, Zigbee, câmeras, IA local, P2P, execução distribuída e APIs comerciais pertencem ao roadmap, a menos que o código e os critérios atuais provem o contrário.
- Testes de CI em runners descartáveis não provam suporte a todos os hardwares físicos nem substituem a validação na VM Ubuntu local.
- Não afirme que uma versão de staging está no notebook. Consulte o PR e a saída de publicação correspondentes.

## Fontes canônicas — consulte nesta ordem conforme o escopo

1. README.md — objetivo, instalação e limites para novos contribuidores.
2. AGENTS.md — regras para agentes, segurança e fronteiras de colaboração.
3. PROJECT_STATUS.md — evidências datadas, estados e validações pendentes.
4. MODULE_MAP.md — árvore funcional, fluxo de dados e dependências.
5. PROJECT_ROADMAP.md — fases, ordem e critérios de conclusão.
6. ARCHITECTURE.md e DECISIONS.md — desenho e decisões vigentes.
7. DEVELOPMENT.md e CONFIGURATION.md — ambiente local e opções.
8. deploy/README.md e VM_VALIDATION.md — operações, recuperação e validação da instalação.
9. SKILL_MAP.md — skill adequada para a área da tarefa.

Se duas fontes divergirem, inspecione código e evidência recente, registre a discrepância e corrija a fonte canônica. Não escolha automaticamente o documento mais otimista.

## Fronteiras que devem ser preservadas

- A API valida autenticação e autorização antes de expor dados ou aceitar comandos.
- Routers coordenam contratos; regras ficam em serviços; acesso persistente fica na camada SQLite.
- MQTT transporta mensagens com tópicos autorizados; não é um substituto para identidade, ACL ou intertravamento físico.
- UI, backend, coleta e operação são módulos independentes com contratos explícitos.
- Mudanças em main.py, schemas.py, database.py, Compose e ACL MQTT exigem coordenação porque afetam mais de um domínio.
- Uma ação física de risco precisa de controles determinísticos locais, confirmação e recuperação; decisão de IA ou visão não basta.

## Roteiro de tarefa para IA

Ao começar, declare: objetivo, módulo dono, contrato afetado, arquivos que pretende tocar, riscos e validação. Inspecione a branch atual antes de editar. Faça uma mudança pequena, preserve comportamento externo ou documente a migração, rode apenas verificações pertinentes e descreva o resultado observado. Atualize status/decisões quando fatos mudarem. Consulte AI_WORKFLOW.md para o passo a passo e o formato de passagem de contexto.

## Cache local

O cache opcional de consulta técnica fica em temp/ e é ignorado pelo Git. Atomizar significa dividir uma referência em notas curtas por conceito com fonte, versão/data, assunto e palavras-chave. Indexar/tokenizar, no material de desenvolvimento atual, significa normalizar termos para busca lexical; não significa criar IDs de tokens de um modelo de linguagem. O cache não é produto, fonte de verdade nem destino para segredos, bases reais, logs ou dados domésticos. Decisões permanentes continuam nos documentos canônicos.