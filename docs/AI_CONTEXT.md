# Contexto estável para agentes de IA

Atualizado: 2026-11-14. Este arquivo é um ponto de orientação, não um snapshot automático. Antes de afirmar o estado atual, consulte os links abaixo e a branch/PR em questão.

## Objetivo

Construir uma plataforma local-first de nó de borda que começa monitorando um host Linux x86_64 de baixo consumo e pode crescer, por módulos independentes, para vários nós, automação doméstica segura, conhecimento e inferência local e distribuição controlada de tarefas. O alvo é Ubuntu Server minimal amd64. Compatibilidade universal ainda não foi comprovada.

## Estado conhecido e limites

- A base atual contém uma API FastAPI, painel React, SQLite, MQTT, agente de telemetria e implantação candidata Compose.
- A instalação systemd/Nginx antiga e a candidata Compose são ambientes separados no notebook de teste. Verifique PROJECT_STATUS.md antes de citar o estado ao vivo.
- O login atualmente usa senha e JWT. USB, Face ID e leitor biométrico não são recursos implementados.
- Telemetria local está presente no nó de teste, mas agregação entre nós não é requisito para o executor de desenvolvimento; será útil quando o Nó Master estiver operacional.
- Multi-nó, biblioteca compartilhada em runtime, Home Assistant, Zigbee, câmeras, IA local, P2P, execução distribuída e APIs comerciais pertencem ao roadmap, a menos que o código e os critérios atuais provem o contrário.
- Testes de CI em runners descartáveis não provam suporte a todos os hardwares físicos. O operador não usará VMs no computador pessoal; use CI hospedada ou simulações.
- Não afirme que uma versão de staging está no notebook. Consulte o PR e a saída de publicação correspondentes.

## Fontes canônicas — consulte nesta ordem conforme o escopo

1. README.md — objetivo, instalação e limites para novos contribuidores.
2. AGENTS.md — regras para agentes, segurança e fronteiras de colaboração.
3. PROJECT_STATUS.md — evidências datadas, estados e validações pendentes.
4. MODULE_MAP.md — árvore funcional, fluxo de dados e dependências.
5. PROJECT_ROADMAP.md — fases, ordem e critérios de conclusão.
6. ARCHITECTURE.md e DECISIONS.md — desenho e decisões vigentes.
7. DEVELOPMENT.md e CONFIGURATION.md — ambiente local e opções.
8. deploy/README.md e VM_VALIDATION.md — operações, recuperação e validação da instalação usando CI remota.
9. AI_MODULE_WORKPLAN.md, AI_EXECUTOR_IMPLEMENTATION.md e AI_DEVELOPMENT_ORCHESTRATION.md — paralelismo e executor externo.
10. VIDEO_RESEARCH_INDEX.md e knowledge/README.md — fontes curadas e busca lexical.
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

## Conhecimento versionado e biblioteca futura

O GitHub é a fonte comum das decisões e do conhecimento técnico curado. `knowledge/catalog/` preserva as fontes e `knowledge/topics/` guarda resumos próprios por conceito. `tools/build_ai_context.py` gera um índice lexical independente de modelo em `knowledge/index/`. Termos normalizados ajudam diferentes IAs a pesquisar; não são IDs do tokenizador interno de um modelo.

A biblioteca consultável e sincronizada dentro do produto ainda é futura. Fontes, licenças, timestamps/páginas e níveis de evidência devem acompanhar cada resumo. Não publique transcrições completas protegidas, segredos, dados domésticos, logs ou telemetria real.

## Cache local opcional

`temp/` pode guardar cache privado e fica ignorada pelo Git. Ela não substitui a biblioteca pública nem os documentos canônicos e nunca deve conter senhas, tokens, bancos reais, logs ou dados domésticos.
