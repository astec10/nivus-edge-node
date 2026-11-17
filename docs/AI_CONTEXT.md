# Nivus — contexto comum para agentes de IA

Este arquivo é a entrada curta para qualquer ferramenta de IA que trabalhe neste repositório. Use os documentos ligados abaixo como fontes de verdade; não deduza que uma ideia planejada já está implementada.

## Objetivo

Criar uma plataforma local-first, modular e econômica para monitorar nós x86_64 com Ubuntu Server minimal, integrar automação residencial com limites explícitos e, em fases futuras, distribuir dados e tarefas entre nós com identidade e capacidade declaradas.

## Estado e escopo

- Para o estado observado no notebook, evidências de CI e pendências, leia [`PROJECT_STATUS.md`](PROJECT_STATUS.md).
- Para fases, critérios e dependências, leia [`PROJECT_ROADMAP.md`](PROJECT_ROADMAP.md).
- A implementação de manutenção e `nivus help` foi integrada no PR #28 e está incluída na release ativa do notebook (`fff64a68`). O update confirmou rebuild, backup, reinício dos serviços, HTTPS 200 e API sem token 401; ainda falta exercitar os comandos de manutenção no host. Consulte `deploy/README.md` e `PROJECT_STATUS.md` antes de afirmar validação funcional completa.
- Em 17/11/2026, o operador atualizou o notebook para `fff64a68f252f0b1290576e30b39ed78fbc15a7a`; build, backup consistente, restart dos serviços, HTTPS 200 e telemetria sem token 401 passaram. A release inclui PRs #66 e #67. O log comprova restart dos containers, não reboot completo; ainda falta revisão visual após Ctrl+F5. A regra móvel do PR #50 só envia OFF com relatório válido e recente em bateria ≤20%; não envia ON. Home Assistant e relé físico seguem pendentes.
- PR #53 integrou proteção contra chamadas de modelo duplicadas quando já existe um draft aberto, remove rótulos obsoletos e comenta o link. A release ativa `fff64a68` é descendente do merge #53; portanto essa correção está na release do notebook. O PR #16 continua draft para revisão humana e nenhuma nova chamada de modelo foi feita.
- Telemetria local está presente no nó de teste, mas telemetria agregada entre nós não é pré-requisito para o executor de desenvolvimento; será útil quando o Nó Master estiver operacional.
- Issue #21: esta proposta adiciona um cadeado para desbloquear a edição local de rascunhos NTP; aplicar continua indisponível enquanto outro cliente gerencia a hora do host.
- Issue #22: a proposta é descobrir sensores de bateria via integração de leitura do Home Assistant e permitir escolha explícita pelo administrador. Não usar User-Agent ou Battery Status API do navegador como autorização.
- Issue #62: o operador escolheu alimentação AC confirmada no nó/UPS para selecionar automaticamente apenas o governor de desempenho suportado, mantendo limites térmicos; atuadores seguem suas regras e overclock permanece manual. A implementação ainda não existe.
- Issue #65: registro seguro inicial integrado pelo PR #66 e incluído na release `fff64a68f252f0b1290576e30b39ed78fbc15a7a`. O agente mínimo de pareamento/heartbeat está implementado no PR #69; os checks de CI hospedada passaram. Os testes usam SQLite temporário, handlers FastAPI reais e transporte simulado; não comprovam comunicação HTTPS end-to-end nem dois dispositivos físicos. Agregação de telemetria, comandos remotos e atualização de frota continuam fora desta entrega.
- Multi-nó operacional, biblioteca compartilhada em runtime, Home Assistant, Zigbee, IA local, P2P e scheduler distribuído continuam planejados até evidência de implementação.
- Issue #68: cadastro administrativo de provedores de IA implementado no PR #72, com CI hospedada aprovada, mas ainda não implantado no notebook. Usa lista + formulário, cadastro manual, chave cifrada com AES-GCM por chave mestra externa e campo mascarado; o segredo nunca volta à API/UI. O teste de conexão é explícito e sem prompt. Limites são armazenados, mas ainda não são aplicados por executor de inferência. Isso não configura `GEMINI_API_KEY` do GitHub Actions. Consulte [AI_PROVIDER_CONNECTORS.md](AI_PROVIDER_CONNECTORS.md).
- Issue #70: o PR de acesso sem porta adiciona seleção de 443 em instalação limpa quando livre e proxy Nginx aditivo para hosts que já ocupam essa porta, preservando a porta Compose alternativa. O script de promoção valida IP/SAN, ocupante de 443, backup, sintaxe, health 200 e telemetria sem token 401; ainda não está instalado no notebook. Não anunciar acesso sem porta como validado antes da promoção real.
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
| Quais módulos dependem de quais? | [`ARCHITECTURE.md`](ARCHITECTURE.md), [`MODULE_MAP.md`](MODULE_MAP.md) |
| Como funciona identidade e heartbeat multi-nó? | [`NODE_REGISTRY.md`](NODE_REGISTRY.md) |
| Qual é a visão e o roadmap? | [`VISION.md`](VISION.md), [`PROJECT_ROADMAP.md`](PROJECT_ROADMAP.md) |
| Como recuperar ou instalar? | [`../deploy/README.md`](../deploy/README.md), [`VM_VALIDATION.md`](VM_VALIDATION.md) |
| Como a biblioteca e os dados de vídeo são curados? | [`AI_WORKFLOW.md`](AI_WORKFLOW.md), [`VIDEO_RESEARCH_INDEX.md`](VIDEO_RESEARCH_INDEX.md), [`../knowledge/README.md`](../knowledge/README.md) |
| Como coordenar agentes externos, dividir módulos e usar o notebook? | [`AI_DEVELOPMENT_ORCHESTRATION.md`](AI_DEVELOPMENT_ORCHESTRATION.md) |
| Como decompor peças paralelas e integrá-las? | [`AI_MODULE_WORKPLAN.md`](AI_MODULE_WORKPLAN.md) |
| Qual executor está disponível e o que ainda requer configuração? | [`AI_EXECUTOR_IMPLEMENTATION.md`](AI_EXECUTOR_IMPLEMENTATION.md) |

## Regra para mudanças

Leia `AGENTS.md`, este contexto, `PROJECT_STATUS.md` e o documento da área antes de editar. Faça uma mudança pequena, preserve contratos, atualize documentação e execute somente validações aplicáveis. Use branch/PR e mantenha aprovação humana antes de produção.

## Scheduler distribuído entre nós

A proposta para perfil de capacidades heterogêneas, inventário validado, cópia assinada do registro, leases e resultados aguardando revisão está em [NODE_CAPABILITY_SCHEDULER.md](NODE_CAPABILITY_SCHEDULER.md). O registro inicial de identidade/heartbeat existe; o scheduler e a validação real de capacidades ainda não estão implementados. Não confundir esta fila de workloads Nivus com Issues/GitHub Actions para PRs de desenvolvimento.