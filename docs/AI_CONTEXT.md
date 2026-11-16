# Nivus — contexto comum para agentes de IA

Este arquivo é a entrada curta para qualquer ferramenta de IA que trabalhe neste repositório. Use os documentos ligados abaixo como fontes de verdade; não deduza que uma ideia planejada já está implementada.

## Objetivo

Criar uma plataforma local-first, modular e econômica para monitorar nós x86_64 com Ubuntu Server minimal, integrar automação residencial com limites explícitos e, em fases futuras, distribuir dados e tarefas entre nós com identidade e capacidade declaradas.

## Estado e escopo

- Para o estado observado no notebook, evidências de CI e pendências, leia [`PROJECT_STATUS.md`](PROJECT_STATUS.md).
- Para fases, critérios e dependências, leia [`PROJECT_ROADMAP.md`](PROJECT_ROADMAP.md).
- A implementação de manutenção e `nivus help` foi integrada à `main` no PR #28. CI passou; o notebook CCE U25 ainda não recebeu nem validou essa release. Consulte `deploy/README.md` e `PROJECT_STATUS.md` antes de afirmar que o recurso está ativo no host.
- Preferências visuais e relógio de Brasília entraram no PR #37; NTP restrito do host nos PRs #40/#41 e três provedores distintos com edição segura no PR #45. Os temas completos do PR #43 oferecem Bento, Glass, SCADA, Cupertino e E-Ink; a seleção fica em Configuração. O PR #44 restaura valores do gráfico imediatamente e deixa mínimos, máximos, origem e hotspots para depois de 3 segundos; contraste alto e movimento reduzido têm efeitos visíveis. O PR #46 acrescenta bateria interna do nó via psutil, com cartão/gráfico e N/D quando indisponível. PRs #44-46 passaram nos checks hospedados. A última versão do notebook comunicada foi c70ed02, anterior ao PR #43; os merges #43-46 ainda precisam ser instalados e confirmados no host. Use o atualizador manual deploy/update.sh; a lista NTP só é aplicada por administrador, protegendo outro cliente ativo, e a bateria interna não é a bateria móvel da issue #22.
- Telemetria local está presente no nó de teste, mas telemetria agregada entre nós não é pré-requisito para o executor de desenvolvimento; será útil quando o Nó Master estiver operacional.
- Multi-nó, biblioteca compartilhada em runtime, Home Assistant, Zigbee, IA local, P2P e scheduler distribuído continuam planejados até evidência de implementação.
- O operador não usará VMs no computador pessoal. Use CI hospedada ou simulações; não solicite instalação local de VM.
- Issue #29: Ubuntu Server completo instalado no USB, com raiz e `NIVUS_DATA` persistentes. O PR #34 foi integrado à `main` no commit `703efa4128f60460910b05ab344b60b082006a7e`; os checks hospedados passaram no head `3a1621dc11d2532853ef83b9ab5ea47f64cfaca5`. A seleção do alvo, seed Subiquity e bootstrap pós-boot estão no código, mas ainda faltam instalar e reiniciar por um USB físico, verificar dados e serviços e testar recuperação. Não há ISO Ubuntu customizada nem qualificação física.
- Acesso atual usa senha/JWT. USB e biometria são opcionais e não estão implementadas.

## Regras invariáveis

1. Preserve autenticação, isolamento, dados persistentes, backup e rollback.
2. Não publique segredos, chaves, banco real, telemetria doméstica, câmeras, rostos ou endereços privados.
3. Não coloque transcrições integrais de vídeos/livros protegidos no repositório. Publique resumo próprio, metadados, links e trechos mínimos quando necessários.
4. Separe alegação do autor, demonstração observada, verificação independente e inferência. Indique a fonte e o nível de confiança.
5. Não instale Hermes, OmniRoute, Jira ou Discord no runtime do nó sem uma decisão separada. Orquestração de desenvolvimento e scheduler Nivus são sistemas diferentes.
6. Ações físicas críticas exigem regras determinísticas, intertravamentos e possibilidade de intervenção humana; IA não deve ser a única autoridade.
7. Não alegue teste, publicação, instalação ou compatibilidade sem saída/evidência correspondente.

## Mapa de leitura

| Pergunta | Fonte |
| --- | --- |
| O que o projeto faz e como contribuir? | [`../README.md`](../README.md), [`../CONTRIBUTING.md`](../CONTRIBUTING.md) |
| Quais módulos dependem de quais? | [`ARCHITECTURE.md`](ARCHITECTURE.md), [`MODULE_MAP.md`](MODULE_MAP.md) quando disponível |
| Qual é a visão e o roadmap? | [`VISION.md`](VISION.md), [`PROJECT_ROADMAP.md`](PROJECT_ROADMAP.md) |
| Como recuperar ou instalar? | [`../deploy/README.md`](../deploy/README.md), [`VM_VALIDATION.md`](VM_VALIDATION.md) |
| Como a biblioteca e os dados de vídeo são curados? | [`AI_WORKFLOW.md`](AI_WORKFLOW.md), [`VIDEO_RESEARCH_INDEX.md`](VIDEO_RESEARCH_INDEX.md), [`../knowledge/README.md`](../knowledge/README.md) |
| Como coordenar agentes externos, dividir módulos e usar o notebook? | [`AI_DEVELOPMENT_ORCHESTRATION.md`](AI_DEVELOPMENT_ORCHESTRATION.md) |
| Como decompor peças paralelas e integrá-las? | [`AI_MODULE_WORKPLAN.md`](AI_MODULE_WORKPLAN.md) |
| Qual executor está disponível e o que ainda requer configuração? | [`AI_EXECUTOR_IMPLEMENTATION.md`](AI_EXECUTOR_IMPLEMENTATION.md) |

## Regra para mudanças

Leia `AGENTS.md`, este contexto, `PROJECT_STATUS.md` e o documento da área antes de editar. Faça uma mudança pequena, preserve contratos, atualize documentação e execute somente validações aplicáveis. Use branch/PR e mantenha aprovação humana antes de produção.
