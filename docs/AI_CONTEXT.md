# Nivus — contexto comum para agentes de IA

Este arquivo é a entrada curta para qualquer ferramenta de IA que trabalhe neste repositório. Use os documentos ligados abaixo como fontes de verdade; não deduza que uma ideia planejada já está implementada.

## Objetivo

Criar uma plataforma local-first, modular e econômica para monitorar nós x86_64 com Ubuntu Server minimal, integrar automação residencial com limites explícitos e, em fases futuras, distribuir dados e tarefas entre nós com identidade e capacidade declaradas.

## Estado e escopo

- Para o estado observado no notebook, evidências de CI e pendências, leia [`PROJECT_STATUS.md`](PROJECT_STATUS.md).
- Para fases, critérios e dependências, leia [`PROJECT_ROADMAP.md`](PROJECT_ROADMAP.md).
- A implementação de manutenção e `nivus help` foi integrada no PR #28 e estava na release do notebook `fff64a68` informada em 17/11. A release ativa `2dfcbc0c2029723e44ff507857c72e7e8b83dfa3` foi confirmada em 21/11; ainda falta exercitar os comandos de manutenção no host. Consulte `deploy/README.md` e `PROJECT_STATUS.md` antes de afirmar validação funcional completa.
- Em 21/11/2026, o atualizador oficial aplicou a release `2dfcbc0c2029723e44ff507857c72e7e8b83dfa3`; backup consistente, health HTTPS 200 e telemetria sem token 401 passaram. Após reload, a viewport móvel confirmou API online, telemetria recente e o padrão `Separado por unidade` com três gráficos empilhados. Android físico e reboot completo ainda não foram verificados. A regra móvel do PR #50 só envia OFF com relatório válido e recente em bateria ≤20%; não envia ON. Home Assistant e relé físico seguem pendentes.
- PR #53 integrou proteção contra chamadas de modelo duplicadas quando já existe um draft aberto, remove rótulos obsoletos e comenta o link. A release `fff64a68` reportada em 17/11 descendia do merge #53; o código está incluído na release ativa `2dfcbc0c2029723e44ff507857c72e7e8b83dfa3`; o PR #16 continua draft para revisão humana e nenhuma nova chamada de modelo foi feita. O PR #16 continua draft para revisão humana e nenhuma nova chamada de modelo foi feita.
- Telemetria local está presente no nó de teste, mas telemetria agregada entre nós não é pré-requisito para o executor de desenvolvimento; será útil quando o Nó Master estiver operacional.
- Issue #21: o PR #45 adicionou o cadeado para desbloquear a edição local de rascunhos NTP; aplicar continua indisponível enquanto outro cliente gerencia a hora do host. A release ativa `2dfcbc0c2029723e44ff507857c72e7e8b83dfa3` inclui a interface; a revisão visual do cadeado e a aplicação real de uma mudança NTP continuam pendentes.
- Issue #22: a proposta é descobrir sensores de bateria via integração de leitura do Home Assistant e permitir escolha explícita pelo administrador. Não usar User-Agent ou Battery Status API do navegador como autorização.
- Issue #62: a implementação candidata `telemetry/power_policy.py` usa uma fonte de energia explicitamente configurada (Linux Mains com entrada direta, ou NUT local), aplica somente governors CPUFreq suportados e cai para o perfil conservador se a fonte estiver ausente/ambígua. Os 12 testes simulados locais passaram; `enabled: false` restaura o governor conservador sem ler a fonte. O timer é opt-in; CI hospedada e validação física ainda pendentes. Atuadores seguem suas regras e overclock permanece manual.
- Issue #65: registro seguro integrado pelo PR #66; PR #96 acrescentou a lista administrativa read-only e PR #97 integrou ingestão autenticada de telemetria por nó, limite de 30 s e retenção de 14 dias. Os quatro workflows hospedados passaram na main após os merges. O histórico gráfico segue no PR #99. Nenhum desses checks comprova TLS ou funcionamento com dois dispositivos físicos; teste real, reboot e atualização de frota continuam pendentes.
- A base de lista, ingestão e histórico API multi-nó está integrada; operação entre dispositivos, atualização coordenada, biblioteca compartilhada em runtime, Home Assistant, Zigbee, IA local, P2P e scheduler distribuído continuam planejados ou dependem de validação física.
- Issue #68: cadastro administrativo de provedores de IA implementado no PR #72 e incluído na release ativa `2dfcbc0c2029723e44ff507857c72e7e8b83dfa3`; ainda falta confirmar seu uso prático no host. A chave fica cifrada com AES-GCM por chave mestra externa e nunca retorna à API/UI. Isso não configura `GEMINI_API_KEY` do GitHub Actions.
- Issue #74: executor runtime integrado no PR #82 e incluído na release ativa `2dfcbc0c2029723e44ff507857c72e7e8b83dfa3`; checks hospedados passaram. Usa classe de dados, reserva de orçamento, timeout, cancelamento e auditoria sem prompt/saída; somente o provedor escolhido, sem fallback, retry ou execução da resposta. Nenhuma chamada real foi feita. Consulte [AI_PROVIDER_CONNECTORS.md](AI_PROVIDER_CONNECTORS.md).
- Issue #70: a release ativa `2dfcbc0c2029723e44ff507857c72e7e8b83dfa3` confirmou HTTPS 200 e API sem token 401; o painel autenticado mostrou telemetria recente e gráficos móveis separados por unidade. A porta `8443` foi preservada; reboot completo e inspeção física no Android continuam pendentes.
- O operador não usará VMs no computador pessoal. Use CI hospedada ou simulações; não solicite instalação local de VM.
- Issue #29: Ubuntu Server completo instalado no USB, com raiz e `NIVUS_DATA` persistentes. O PR #34 foi integrado à `main` no commit `703efa4128f60460910b05ab344b60b082006a7e`; os checks hospedados passaram no head `3a1621dc11d2532853ef83b9ab5ea47f64cfaca5`. A seleção do alvo, seed Subiquity e bootstrap pós-boot estão no código, mas ainda faltam instalar e reiniciar por um USB físico, verificar dados e serviços e testar recuperação. Não há ISO Ubuntu customizada nem qualificação física.
- Acesso atual usa senha/JWT. USB e biometria são opcionais e não estão implementadas.

## Canal SSH de manutenção

Relato do operador em 23/11/2026: uma consulta de diagnóstico `status` respondeu pelo canal restrito. Uma tentativa independente nesta sessão não autenticou; disponibilidade e configuração atuais não estão verificadas. A existência do canal não autoriza conexão ou operação. Exija autorização específica por tarefa, valide identidade e chave de host e use somente operações explicitamente autorizadas. Não presuma shell, sudo, Docker, atualização ou deploy. Mantenha identificadores de conexão e credenciais fora do repositório. A issue #130 continua aberta para o desenho completo do canal.

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
